import streamlit as st
import requests
from pathlib import Path
from PIL import Image
import io


# ============================================================
# YOLO IMPORT
# ============================================================

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    YOLO_IMPORT_ERROR = ""
except Exception as e:
    YOLO_AVAILABLE = False
    YOLO_IMPORT_ERROR = str(e)


# ============================================================
# FASTAPI BACKEND
# ============================================================

API_URL = "https://roadwatch-ai-production.up.railway.app"


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="RoadWatch AI",
    page_icon="🚧",
    layout="wide"
)


# ============================================================
# YOLO MODEL PATH
# ============================================================

# Railway Root Directory = /frontend
# Therefore app.py is inside /frontend
# and best.pt should be inside /frontend/AI/best.pt

PROJECT_ROOT = Path(__file__).resolve().parent

MODEL_CANDIDATES = [
    PROJECT_ROOT / "AI" / "best.pt",
    PROJECT_ROOT / "ai" / "best.pt",
    PROJECT_ROOT / "AI" / "weights" / "best.pt",
    PROJECT_ROOT / "ai" / "weights" / "best.pt",
    PROJECT_ROOT / "best.pt",
]

MODEL_PATH = next(
    (path for path in MODEL_CANDIDATES if path.is_file()),
    None
)


# ============================================================
# DEBUG INFORMATION
# ============================================================

st.write("YOLO_AVAILABLE:", YOLO_AVAILABLE)
st.write(
    "MODEL_PATH:",
    str(MODEL_PATH) if MODEL_PATH else "NOT FOUND"
)

if not YOLO_AVAILABLE:
    st.error("YOLO IMPORT ERROR")
    st.code(YOLO_IMPORT_ERROR)

if MODEL_PATH:
    st.success("MODEL FILE FOUND")
    st.write("MODEL EXISTS:", MODEL_PATH.exists())
else:
    st.error("MODEL FILE NOT FOUND")

    # Show exactly where Railway is looking
    st.write("PROJECT ROOT:", str(PROJECT_ROOT))

    st.write("Files detected inside frontend:")

    try:
        for item in PROJECT_ROOT.rglob("*"):
            if item.is_file():
                st.write(str(item.relative_to(PROJECT_ROOT)))
    except Exception as e:
        st.code(str(e))


# ============================================================
# LOAD YOLO MODEL
# ============================================================

@st.cache_resource
def load_yolo_model(model_path):

    if not YOLO_AVAILABLE:
        return None

    if model_path is None:
        return None

    try:
        return YOLO(str(model_path))
    except Exception as e:
        st.error("YOLO MODEL LOAD ERROR")
        st.code(str(e))
        return None


model = load_yolo_model(MODEL_PATH)

if model is not None:
    st.success("AI MODEL LOADED SUCCESSFULLY")
else:
    st.warning(
        "AI model is currently unavailable. "
        "The rest of RoadWatch AI can still be used."
    )


# ============================================================
# SESSION STATE
# ============================================================

if "role" not in st.session_state:
    st.session_state["role"] = None

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

if "user_name" not in st.session_state:
    st.session_state["user_name"] = None


# ============================================================
# AI DETECTION
# ============================================================

def show_ai_result(uploaded_file):

    if model is None:

        st.warning(
            "AI model is not available. "
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

        annotated = result.plot()

        annotated_image = Image.fromarray(
            annotated[:, :, ::-1]
        )

        st.image(
            annotated_image,
            caption="AI analysis result",
            use_container_width=True
        )

        names = result.names
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:

            st.info(
                "No road damage objects were detected."
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

        # ====================================================
        # SEVERITY / RCI
        # ====================================================

        max_confidence = max(
            d["confidence"]
            for d in detections
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

    except Exception as e:

        st.error("AI inference failed.")
        st.code(str(e))


# ============================================================
# TITLE
# ============================================================

st.title("🚧 RoadWatch AI")

st.subheader(
    "AI-Powered Road Damage Reporting System"
)


# ============================================================
# HOME / ROLE SELECTION
# ============================================================

if st.session_state["role"] is None:

    st.write(
        "Report damaged roads and help authorities "
        "respond faster."
    )

    st.divider()

    st.header("Choose your role")

    col1, col2 = st.columns(2)

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
            st.rerun()

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
            st.rerun()


# ============================================================
# CITIZEN LOGIN / REGISTER
# ============================================================

elif (
    st.session_state["role"] == "citizen"
    and not st.session_state["logged_in"]
):

    st.header("👤 Citizen Portal")

    option = st.radio(
        "Choose an option",
        ["Login", "Register"],
        horizontal=True
    )

    if option == "Register":

        st.subheader("Create Citizen Account")

        with st.form("citizen_register_form"):

            name = st.text_input("Name")

            email = st.text_input("Email")

            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Register",
                use_container_width=True
            )

        if submitted:

            if not name or not email or not password:

                st.warning(
                    "Please fill all fields."
                )

            else:

                try:

                    response = requests.post(
                        f"{API_URL}/auth/register",
                        json={
                            "name": name,
                            "email": email,
                            "password": password,
                            "role": "citizen"
                        },
                        timeout=30
                    )

                    if response.status_code in [200, 201]:

                        st.success(
                            "Registration successful! "
                            "You can now login."
                        )

                    else:

                        st.error(
                            f"Registration failed "
                            f"({response.status_code})"
                        )

                        st.code(response.text)

                except requests.exceptions.RequestException as e:

                    st.error(
                        "Cannot connect to FastAPI."
                    )

                    st.code(str(e))

    else:

        st.subheader("Citizen Login")

        with st.form("citizen_login_form"):

            email = st.text_input(
                "Email",
                key="citizen_login_email"
            )

            password = st.text_input(
                "Password",
                type="password",
                key="citizen_login_password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if submitted:

            if not email.strip() or not password:

                st.warning(
                    "Please enter your email and password."
                )

            else:

                try:

                    response = requests.post(
                        f"{API_URL}/auth/login",
                        json={
                            "email": email.strip(),
                            "password": password
                        },
                        timeout=30
                    )

                    if response.status_code == 200:

                        result = response.json()

                        st.session_state["logged_in"] = True
                        st.session_state["user_id"] = result["user_id"]
                        st.session_state["user_name"] = result["name"]

                        st.success("Login successful!")

                        st.rerun()

                    else:

                        st.error(
                            f"Login failed "
                            f"({response.status_code})"
                        )

                        st.code(response.text)

                except requests.exceptions.RequestException as e:

                    st.error(
                        "Cannot connect to FastAPI."
                    )

                    st.code(str(e))


# ============================================================
# CITIZEN DASHBOARD
# ============================================================

elif (
    st.session_state["role"] == "citizen"
    and st.session_state["logged_in"]
):

    st.header("👤 Citizen Dashboard")

    st.success(
        f"Welcome, {st.session_state['user_name']}!"
    )

    st.divider()

    st.header("📝 Report Road Damage")

    description = st.text_area(
        "Describe the road damage",
        placeholder="Example: Large pothole near the main road..."
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
        type=["jpg", "jpeg", "png"]
    )

    if st.button(
        "Submit Road Damage Report",
        use_container_width=True
    ):

        if not description or not address:

            st.warning(
                "Please provide the description and address."
            )

        elif uploaded_file is None:

            st.warning(
                "Please upload a road image."
            )

        else:

            try:

                response = requests.post(
                    f"{API_URL}/reports/",
                    params={
                        "user_id": st.session_state["user_id"]
                    },
                    json={
                        "description": description,
                        "latitude": latitude,
                        "longitude": longitude,
                        "address": address
                    },
                    timeout=30
                )

                if response.status_code == 200:

                    report_result = response.json()

                    report_id = report_result["report_id"]

                    st.success(
                        f"Road report submitted successfully! "
                        f"Report ID: {report_id}"
                    )

                    image_response = requests.post(
                        f"{API_URL}/images/upload/{report_id}",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                uploaded_file.type
                            )
                        },
                        timeout=60
                    )

                    if image_response.status_code == 200:

                        st.success(
                            "Road image uploaded successfully!"
                        )

                        show_ai_result(uploaded_file)

                    else:

                        st.error(
                            "Report was created, "
                            "but image upload failed."
                        )

                        st.code(image_response.text)

                else:

                    st.error(
                        f"Report submission failed "
                        f"({response.status_code})"
                    )

                    st.code(response.text)

            except requests.exceptions.RequestException as e:

                st.error(
                    "Cannot connect to FastAPI."
                )

                st.code(str(e))

    # ========================================================
    # MY REPORTS
    # ========================================================

    st.divider()

    st.header("📋 My Reports")

    try:

        response = requests.get(
            f"{API_URL}/reports/",
            timeout=30
        )

        if response.status_code == 200:

            result = response.json()

            reports = result.get("reports", [])

            my_reports = [
                report
                for report in reports
                if report.get("user_id")
                == st.session_state["user_id"]
            ]

            if my_reports:

                for report in my_reports:

                    st.subheader(
                        f"🚧 Report #{report.get('report_id')}"
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
                    "You have not submitted any reports yet."
                )

        else:

            st.error(
                f"Unable to load reports "
                f"({response.status_code})"
            )

    except requests.exceptions.RequestException as e:

        st.error(
            "Cannot connect to FastAPI."
        )

        st.code(str(e))

    st.divider()

    if st.button(
        "🚪 Logout",
        use_container_width=True
    ):

        st.session_state.clear()
        st.rerun()


# ============================================================
# OFFICIAL LOGIN
# ============================================================

elif (
    st.session_state["role"] == "official"
    and not st.session_state["logged_in"]
):

    st.header("👮 Official Portal")

    st.subheader("Official Login")

    with st.form("official_login_form"):

        email = st.text_input(
            "Official Email",
            key="official_login_email"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="official_login_password"
        )

        submitted = st.form_submit_button(
            "Official Login",
            use_container_width=True
        )

    if submitted:

        if not email.strip() or not password:

            st.warning(
                "Please enter your email and password."
            )

        else:

            try:

                response = requests.post(
                    f"{API_URL}/auth/login",
                    json={
                        "email": email.strip(),
                        "password": password
                    },
                    timeout=30
                )

                if response.status_code == 200:

                    result = response.json()

                    if result.get("role") != "official":

                        st.error(
                            "This account is not an official account."
                        )

                    else:

                        st.session_state["logged_in"] = True
                        st.session_state["user_id"] = result["user_id"]
                        st.session_state["user_name"] = result["name"]

                        st.success(
                            "Official login successful!"
                        )

                        st.rerun()

                elif response.status_code == 401:

                    st.error(
                        "Invalid email or password."
                    )

                else:

                    st.error(
                        f"Login failed "
                        f"({response.status_code})"
                    )

                    st.code(response.text)

            except requests.exceptions.RequestException as e:

                st.error(
                    "Cannot connect to FastAPI."
                )

                st.code(str(e))


# ============================================================
# OFFICIAL DASHBOARD
# ============================================================

elif (
    st.session_state["role"] == "official"
    and st.session_state["logged_in"]
):

    st.header("👮 Official Dashboard")

    st.success(
        f"Welcome, {st.session_state['user_name']}!"
    )

    st.write(
        "Review submitted road damage reports "
        "and monitor road-condition activity."
    )

    try:

        response = requests.get(
            f"{API_URL}/reports/",
            timeout=30
        )

        if response.status_code != 200:

            st.error(
                f"Unable to load reports "
                f"({response.status_code})"
            )

            st.code(response.text)

        else:

            result = response.json()

            reports = result.get("reports", [])

            st.divider()

            st.header("📊 RoadWatch Analytics")

            total_reports = len(reports)

            submitted_count = sum(
                1 for r in reports
                if r.get("status") == "submitted"
            )

            under_review_count = sum(
                1 for r in reports
                if r.get("status") == "under_review"
            )

            in_progress_count = sum(
                1 for r in reports
                if r.get("status") == "in_progress"
            )

            resolved_count = sum(
                1 for r in reports
                if r.get("status") == "resolved"
            )

            rejected_count = sum(
                1 for r in reports
                if r.get("status") == "rejected"
            )

            m1, m2, m3 = st.columns(3)

            with m1:
                st.metric("Total Reports", total_reports)

            with m2:
                st.metric("Under Review", under_review_count)

            with m3:
                st.metric("Resolved", resolved_count)

            m4, m5, m6 = st.columns(3)

            with m4:
                st.metric("Submitted", submitted_count)

            with m5:
                st.metric("In Progress", in_progress_count)

            with m6:
                st.metric("Rejected", rejected_count)

            if total_reports > 0:

                st.subheader(
                    "📈 Report Status Distribution"
                )

                st.bar_chart(
                    {
                        "Submitted": submitted_count,
                        "Under Review": under_review_count,
                        "In Progress": in_progress_count,
                        "Resolved": resolved_count,
                        "Rejected": rejected_count
                    }
                )

            st.divider()

            st.header("📋 All Road Reports")

            if reports:

                for report in reports:

                    report_id = report.get("report_id")

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

                        try:

                            update_response = requests.put(
                                f"{API_URL}/reports/"
                                f"{report_id}/status",
                                params={
                                    "status": new_status,
                                    "official_user_id":
                                        st.session_state["user_id"]
                                },
                                timeout=30
                            )

                            if update_response.status_code == 200:

                                st.success(
                                    f"Report #{report_id} "
                                    "updated successfully!"
                                )

                                st.rerun()

                            else:

                                st.error(
                                    f"Update failed "
                                    f"({update_response.status_code})"
                                )

                                st.code(
                                    update_response.text
                                )

                        except requests.exceptions.RequestException as e:

                            st.error(
                                "Cannot connect to FastAPI."
                            )

                            st.code(str(e))

                    try:

                        history_response = requests.get(
                            f"{API_URL}/reports/"
                            f"{report_id}/history",
                            timeout=30
                        )

                        if history_response.status_code == 200:

                            history_result = history_response.json()

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

                    except requests.exceptions.RequestException:
                        pass

                    st.divider()

            else:

                st.info(
                    "No road reports available."
                )

    except requests.exceptions.RequestException as e:

        st.error(
            "Cannot connect to FastAPI."
        )

        st.code(str(e))

    st.divider()

    if st.button(
        "🚪 Official Logout",
        use_container_width=True
    ):

        st.session_state.clear()
        st.rerun()
