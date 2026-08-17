import streamlit as st
import requests
from pathlib import Path
from PIL import Image
import io

# ==================================================
# OPTIONAL YOLO IMPORT
# ==================================================

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception:
    YOLO_AVAILABLE = False


API_URL = "http://127.0.0.1:8000"


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="RoadWatch AI",
    page_icon="🚧",
    layout="wide"
)


# ==================================================
# PROJECT PATHS / AI MODEL
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_CANDIDATES = [
    PROJECT_ROOT / "ai" / "best.pt",
    PROJECT_ROOT / "ai" / "weights" / "best.pt",
    PROJECT_ROOT / "best.pt",
    PROJECT_ROOT / "yolov8n.pt",
]

MODEL_PATH = next(
    (path for path in MODEL_CANDIDATES if path.exists()),
    None
)


@st.cache_resource
def load_yolo_model(model_path):
    if not YOLO_AVAILABLE or model_path is None:
        return None

    try:
        return YOLO(str(model_path))
    except Exception:
        return None


model = load_yolo_model(MODEL_PATH)


# ==================================================
# SESSION STATE
# ==================================================

if "role" not in st.session_state:
    st.session_state["role"] = None

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

if "user_name" not in st.session_state:
    st.session_state["user_name"] = None


# ==================================================
# AI DETECTION FUNCTION
# ==================================================

def show_ai_result(uploaded_file):

    if model is None:

        st.warning(
            "AI model is not available yet. "
            "The image was uploaded successfully."
        )

        return

    try:

        image_bytes = uploaded_file.getvalue()

        image = Image.open(
            io.BytesIO(image_bytes)
        ).convert("RGB")

        results = model.predict(
            source=image,
            conf=0.25,
            verbose=False
        )

        result = results[0]

        st.subheader("🤖 AI Detection")

        # ------------------------------------------
        # SHOW ANNOTATED IMAGE
        # ------------------------------------------

        annotated = result.plot()

        annotated_image = Image.fromarray(
            annotated[:, :, ::-1]
        )

        st.image(
            annotated_image,
            caption="AI analysis result",
            use_column_width=True
        )

        # ------------------------------------------
        # DETECTIONS
        # ------------------------------------------

        names = result.names
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:

            st.info(
                "No objects were detected by the current model."
            )

            if MODEL_PATH:
                st.caption(
                    f"Current model: {MODEL_PATH.name}"
                )

            return

        detections = []

        for i in range(len(boxes)):

            class_id = int(
                boxes.cls[i].item()
            )

            confidence = float(
                boxes.conf[i].item()
            )

            if isinstance(names, dict):

                class_name = names.get(
                    class_id,
                    str(class_id)
                )

            else:

                class_name = names[class_id]

            detections.append(
                {
                    "class": class_name,
                    "confidence": confidence
                }
            )

        st.success(
            f"{len(detections)} object(s) detected."
        )

        for detection in detections:

            st.write(
                f"• **{detection['class']}** — "
                f"{detection['confidence'] * 100:.1f}% confidence"
            )

        # ------------------------------------------
        # SEVERITY / RCI
        # ------------------------------------------

        if MODEL_PATH and MODEL_PATH.name == "best.pt":

            max_confidence = max(
                detection["confidence"]
                for detection in detections
            )

            if (
                len(detections) >= 3
                or max_confidence >= 0.80
            ):

                severity = "High"
                rci = 3

            elif (
                len(detections) >= 2
                or max_confidence >= 0.60
            ):

                severity = "Medium"
                rci = 2

            else:

                severity = "Low"
                rci = 1

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Estimated Severity",
                    severity
                )

            with col2:

                st.metric(
                    "RCI Score",
                    f"{rci}/3"
                )

        else:

            st.warning(
                "Severity/RCI will be enabled after "
                "the road-damage-trained model "
                "(best.pt) is added."
            )

    except Exception as e:

        st.error("AI inference failed.")
        st.code(str(e))


# ==================================================
# TITLE
# ==================================================

st.title("🚧 RoadWatch AI")

st.subheader(
    "AI-Powered Road Damage Reporting System"
)


# ==================================================
# HOME / ROLE SELECTION
# ==================================================

if st.session_state["role"] is None:

    st.write(
        "Report damaged roads and help authorities "
        "respond faster."
    )

    st.divider()

    st.header("Choose your role")

    col1, col2 = st.columns(2)

    # ----------------------------------------------
    # CITIZEN
    # ----------------------------------------------

    with col1:

        st.subheader("👤 Citizen")

        st.write(
            "Report road damage, upload images, "
            "and track your submitted reports."
        )

        if st.button(
            "Continue as Citizen",
            use_container_width=True
        ):

            st.session_state["role"] = "citizen"

            st.experimental_rerun()

    # ----------------------------------------------
    # OFFICIAL
    # ----------------------------------------------

    with col2:

        st.subheader("👮 Official")

        st.write(
            "View road damage reports, review "
            "complaints, and update report status."
        )

        if st.button(
            "Continue as Official",
            use_container_width=True
        ):

            st.session_state["role"] = "official"

            st.experimental_rerun()


# ==================================================
# CITIZEN LOGIN / REGISTER
# ==================================================

elif (
    st.session_state["role"] == "citizen"
    and st.session_state["logged_in"] is False
):

    st.header("👤 Citizen Portal")

    option = st.radio(
        "Choose an option",
        ["Login", "Register"],
        horizontal=True
    )

    # ==================================================
    # CITIZEN REGISTER
    # ==================================================

    if option == "Register":

        st.subheader(
            "Create Citizen Account"
        )

        name = st.text_input("Name")

        email = st.text_input("Email")

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button(
            "Register",
            use_container_width=True
        ):

            if not name or not email or not password:

                st.warning(
                    "Please fill all fields."
                )

            else:

                data = {
                    "name": name,
                    "email": email,
                    "password": password,
                    "role": "citizen"
                }

                try:

                    response = requests.post(
                        f"{API_URL}/auth/register",
                        json=data
                    )

                    if response.status_code == 200:

                        try:

                            result = response.json()

                            st.success(
                                result.get(
                                    "message",
                                    "Registration successful!"
                                )
                            )

                        except ValueError:

                            st.success(
                                "Registration successful!"
                            )

                    else:

                        st.error(
                            f"Registration failed. "
                            f"Status code: "
                            f"{response.status_code}"
                        )

                        st.code(
                            response.text
                        )

                except requests.exceptions.ConnectionError:

                    st.error(
                        "Cannot connect to FastAPI. "
                        "Make sure the backend is running."
                    )

    # ==================================================
    # CITIZEN LOGIN
    # ==================================================

    else:

        st.subheader(
            "Citizen Login"
        )

        email = st.text_input("Email")

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button(
            "Login",
            use_container_width=True
        ):

            if not email or not password:

                st.warning(
                    "Please enter email and password."
                )

            else:

                data = {
                    "email": email,
                    "password": password
                }

                try:

                    response = requests.post(
                        f"{API_URL}/auth/login",
                        json=data
                    )

                    if response.status_code == 200:

                        try:

                            result = response.json()

                            st.session_state[
                                "logged_in"
                            ] = True

                            st.session_state[
                                "user_id"
                            ] = result["user_id"]

                            st.session_state[
                                "user_name"
                            ] = result["name"]

                            st.success(
                                "Login successful!"
                            )

                            st.experimental_rerun()

                        except ValueError:

                            st.error(
                                "FastAPI returned "
                                "an invalid response."
                            )

                    else:

                        st.error(
                            f"Login failed. "
                            f"Status code: "
                            f"{response.status_code}"
                        )

                        st.code(
                            response.text
                        )

                except requests.exceptions.ConnectionError:

                    st.error(
                        "Cannot connect to FastAPI. "
                        "Make sure the backend is running."
                    )


# ==================================================
# CITIZEN DASHBOARD
# ==================================================

elif (
    st.session_state["role"] == "citizen"
    and st.session_state["logged_in"] is True
):

    st.header("👤 Citizen Dashboard")

    st.success(
        f"Welcome, "
        f"{st.session_state['user_name']}!"
    )

    # ==================================================
    # REPORT ROAD DAMAGE
    # ==================================================

    st.divider()

    st.header(
        "📝 Report Road Damage"
    )

    description = st.text_area(
        "Describe the road damage",
        placeholder=(
            "Example: Large pothole near the main road..."
        )
    )

    latitude = st.number_input(
        "Latitude",
        value=9.9252,
        format="%.6f"
    )

    longitude = st.number_input(
        "Longitude",
        value=78.1198,
        format="%.6f"
    )

    address = st.text_input(
        "Address / Location",
        placeholder="Example: Madurai Main Road"
    )

    uploaded_file = st.file_uploader(
        "Upload Road Image",
        type=[
            "jpg",
            "jpeg",
            "png"
        ]
    )

    if st.button(
        "Submit Road Damage Report",
        use_container_width=True
    ):

        if not description or not address:

            st.warning(
                "Please provide the description "
                "and address."
            )

        elif uploaded_file is None:

            st.warning(
                "Please upload a road image."
            )

        else:

            report_data = {
                "description": description,
                "latitude": latitude,
                "longitude": longitude,
                "address": address
            }

            try:

                # --------------------------------------
                # CREATE REPORT
                # --------------------------------------

                response = requests.post(
                    f"{API_URL}/reports/",
                    params={
                        "user_id":
                            st.session_state["user_id"]
                    },
                    json=report_data
                )

                if response.status_code == 200:

                    report_result = response.json()

                    report_id = (
                        report_result["report_id"]
                    )

                    st.success(
                        f"Road report submitted "
                        f"successfully! "
                        f"Report ID: {report_id}"
                    )

                    # ----------------------------------
                    # UPLOAD IMAGE
                    # ----------------------------------

                    image_response = requests.post(
                        f"{API_URL}/images/upload/"
                        f"{report_id}",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                uploaded_file.type
                            )
                        }
                    )

                    if image_response.status_code == 200:

                        st.success(
                            "Road image uploaded "
                            "successfully!"
                        )

                        # ----------------------------------
                        # RUN AI
                        # ----------------------------------

                        show_ai_result(
                            uploaded_file
                        )

                    else:

                        st.error(
                            "Report was created, "
                            "but image upload failed."
                        )

                        st.code(
                            image_response.text
                        )

                else:

                    st.error(
                        f"Report submission failed. "
                        f"Status code: "
                        f"{response.status_code}"
                    )

                    st.code(
                        response.text
                    )

            except requests.exceptions.ConnectionError:

                st.error(
                    "Cannot connect to FastAPI. "
                    "Make sure the backend is running."
                )

    # ==================================================
    # MY REPORTS
    # ==================================================

    st.divider()

    st.header(
        "📋 My Reports"
    )

    try:

        response = requests.get(
            f"{API_URL}/reports/"
        )

        if response.status_code == 200:

            result = response.json()

            reports = result.get(
                "reports",
                []
            )

            my_reports = [
                report
                for report in reports
                if report.get("user_id")
                == st.session_state["user_id"]
            ]

            if my_reports:

                for report in my_reports:

                    st.subheader(
                        f"🚧 Report "
                        f"#{report.get('report_id')}"
                    )

                    st.write(
                        f"**Description:** "
                        f"{report.get('description', 'N/A')}"
                    )

                    st.write(
                        f"**Location:** "
                        f"{report.get('address', 'N/A')}"
                    )

                    st.write(
                        f"**Status:** "
                        f"{report.get('status', 'N/A')}"
                    )

                    st.divider()

            else:

                st.info(
                    "You have not submitted "
                    "any reports yet."
                )

        else:

            st.error(
                f"Unable to load reports. "
                f"Status code: "
                f"{response.status_code}"
            )

            st.code(
                response.text
            )

    except requests.exceptions.ConnectionError:

        st.error(
            "Cannot connect to FastAPI. "
            "Make sure the backend is running."
        )

    # ==================================================
    # CITIZEN LOGOUT
    # ==================================================

    st.divider()

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.session_state.clear()

        st.experimental_rerun()


# ==================================================
# OFFICIAL LOGIN
# ==================================================

elif (
    st.session_state["role"] == "official"
    and st.session_state["logged_in"] is False
):

    st.header(
        "👮 Official Portal"
    )

    st.subheader(
        "Official Login"
    )

    email = st.text_input(
        "Official Email"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button(
        "Official Login",
        use_container_width=True
    ):

        if not email or not password:

            st.warning(
                "Please enter your email and password."
            )

        else:

            data = {
                "email": email,
                "password": password
            }

            try:

                response = requests.post(
                    f"{API_URL}/auth/login",
                    json=data
                )

                if response.status_code == 200:

                    result = response.json()

                    if result.get("role") != "official":

                        st.error(
                            "This account is not "
                            "an official account."
                        )

                    else:

                        st.session_state[
                            "logged_in"
                        ] = True

                        st.session_state[
                            "user_id"
                        ] = result["user_id"]

                        st.session_state[
                            "user_name"
                        ] = result["name"]

                        st.success(
                            "Official login successful!"
                        )

                        st.experimental_rerun()

                else:

                    st.error(
                        f"Login failed. "
                        f"Status code: "
                        f"{response.status_code}"
                    )

                    st.code(
                        response.text
                    )

            except requests.exceptions.ConnectionError:

                st.error(
                    "Cannot connect to FastAPI. "
                    "Make sure the backend is running."
                )


# ==================================================
# OFFICIAL DASHBOARD
# ==================================================

elif (
    st.session_state["role"] == "official"
    and st.session_state["logged_in"] is True
):

    st.header(
        "👮 Official Dashboard"
    )

    st.success(
        f"Welcome, "
        f"{st.session_state['user_name']}!"
    )

    st.write(
        "Review submitted road damage reports "
        "and monitor road-condition activity."
    )

    # ==================================================
    # LOAD REPORT DATA
    # ==================================================

    try:

        response = requests.get(
            f"{API_URL}/reports/"
        )

        if response.status_code != 200:

            st.error(
                f"Unable to load reports. "
                f"Status code: {response.status_code}"
            )

            st.code(
                response.text
            )

        else:

            result = response.json()

            reports = result.get(
                "reports",
                []
            )

            # ==================================================
            # ANALYTICS / VISUALIZATION
            # ==================================================

            st.divider()

            st.header(
                "📊 RoadWatch Analytics"
            )

            total_reports = len(reports)

            submitted_count = sum(
                1
                for report in reports
                if report.get("status") == "submitted"
            )

            under_review_count = sum(
                1
                for report in reports
                if report.get("status") == "under_review"
            )

            in_progress_count = sum(
                1
                for report in reports
                if report.get("status") == "in_progress"
            )

            resolved_count = sum(
                1
                for report in reports
                if report.get("status") == "resolved"
            )

            rejected_count = sum(
                1
                for report in reports
                if report.get("status") == "rejected"
            )

            # ----------------------------------------------
            # METRICS
            # ----------------------------------------------

            metric1, metric2, metric3 = st.columns(3)

            with metric1:

                st.metric(
                    "Total Reports",
                    total_reports
                )

            with metric2:

                st.metric(
                    "Under Review",
                    under_review_count
                )

            with metric3:

                st.metric(
                    "Resolved",
                    resolved_count
                )

            metric4, metric5, metric6 = st.columns(3)

            with metric4:

                st.metric(
                    "Submitted",
                    submitted_count
                )

            with metric5:

                st.metric(
                    "In Progress",
                    in_progress_count
                )

            with metric6:

                st.metric(
                    "Rejected",
                    rejected_count
                )

            # ==================================================
            # STATUS CHART
            # ==================================================

            if total_reports > 0:

                st.subheader(
                    "📈 Report Status Distribution"
                )

                status_data = {
                    "Submitted": submitted_count,
                    "Under Review": under_review_count,
                    "In Progress": in_progress_count,
                    "Resolved": resolved_count,
                    "Rejected": rejected_count
                }

                st.bar_chart(
                    status_data
                )

                # ----------------------------------------------
                # PIE-STYLE VISUALIZATION USING DATAFRAME
                # ----------------------------------------------

                try:

                    import pandas as pd

                    chart_df = pd.DataFrame(
                        {
                            "Status": [
                                "Submitted",
                                "Under Review",
                                "In Progress",
                                "Resolved",
                                "Rejected"
                            ],
                            "Reports": [
                                submitted_count,
                                under_review_count,
                                in_progress_count,
                                resolved_count,
                                rejected_count
                            ]
                        }
                    )

                    st.subheader(
                        "📊 Status Summary"
                    )

                    st.dataframe(
                        chart_df,
                        use_container_width=True
                    )

                except Exception:

                    pass

            else:

                st.info(
                    "No report data available for analytics yet."
                )

            # ==================================================
            # ALL ROAD REPORTS
            # ==================================================

            st.divider()

            st.header(
                "📋 All Road Reports"
            )

            if reports:

                for report in reports:

                    report_id = report.get(
                        "report_id"
                    )

                    st.subheader(
                        f"🚧 Report #{report_id}"
                    )

                    st.write(
                        f"**Description:** "
                        f"{report.get('description', 'N/A')}"
                    )

                    st.write(
                        f"**Location:** "
                        f"{report.get('address', 'N/A')}"
                    )

                    st.write(
                        f"**Latitude:** "
                        f"{report.get('latitude', 'N/A')}"
                    )

                    st.write(
                        f"**Longitude:** "
                        f"{report.get('longitude', 'N/A')}"
                    )

                    st.write(
                        f"**Current Status:** "
                        f"{report.get('status', 'N/A')}"
                    )

                    # ------------------------------------------
                    # STATUS UPDATE
                    # ------------------------------------------

                    new_status = st.selectbox(
                        "Update Status",
                        [
                            "submitted",
                            "under_review",
                            "in_progress",
                            "resolved",
                            "rejected"
                        ],
                        key=f"status_{report_id}"
                    )

                    if st.button(
                        f"Update Report #{report_id}",
                        key=f"update_{report_id}"
                    ):

                        update_response = requests.put(
                            f"{API_URL}/reports/"
                            f"{report_id}/status",
                            params={
                                "status": new_status,
                                "official_user_id":
                                    st.session_state["user_id"]
                            }
                        )

                        if update_response.status_code == 200:

                            st.success(
                                f"Report #{report_id} "
                                "updated successfully!"
                            )

                            st.json(
                                update_response.json()
                            )

                            st.experimental_rerun()

                        else:

                            st.error(
                                f"Update failed. "
                                f"Status code: "
                                f"{update_response.status_code}"
                            )

                            st.code(
                                update_response.text
                            )

                    # ------------------------------------------
                    # STATUS HISTORY
                    # ------------------------------------------

                    history_response = requests.get(
                        f"{API_URL}/reports/"
                        f"{report_id}/history"
                    )

                    if history_response.status_code == 200:

                        history_result = (
                            history_response.json()
                        )

                        history = history_result.get(
                            "history",
                            []
                        )

                        if history:

                            with st.expander(
                                "View Status History"
                            ):

                                for item in history:

                                    st.write(
                                        f"**"
                                        f"{item.get('old_status', 'N/A')}"
                                        f" → "
                                        f"{item.get('new_status', 'N/A')}"
                                        f"**"
                                    )

                                    st.caption(
                                        f"Official ID: "
                                        f"{item.get('changed_by', 'N/A')} | "
                                        f"Time: "
                                        f"{item.get('changed_at', 'N/A')}"
                                    )

                    st.divider()

            else:

                st.info(
                    "No road reports available."
                )

    except requests.exceptions.ConnectionError:

        st.error(
            "Cannot connect to FastAPI. "
            "Make sure the backend is running."
        )

    # ==================================================
    # OFFICIAL LOGOUT
    # ==================================================

    st.divider()

    if st.button(
        "🚪 Official Logout",
        use_container_width=True
    ):

        st.session_state.clear()

        st.experimental_rerun()