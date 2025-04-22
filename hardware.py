import streamlit as st
import requests
from groq import Groq
from PIL import Image
import sqlite3
import io
import base64
import time
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# Load environment variables
load_dotenv()

# Initialize Groq client
try:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    st.error(f"Failed to initialize Groq client: {str(e)}")
    st.stop()

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('hardware_support.db')
    c = conn.cursor()
    
    # Create Customers table
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  service_tag TEXT UNIQUE,
                  customer_name TEXT,
                  customer_email TEXT,
                  customer_phone TEXT,
                  customer_address TEXT,
                  laptop_model TEXT,
                  purchase_date TEXT,
                  warranty_end_date TEXT,
                  warranty_valid INTEGER)''')
    
    # Create Service Technicians table
    c.execute('''CREATE TABLE IF NOT EXISTS technicians
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  email TEXT,
                  phone TEXT,
                  specialization TEXT,
                  location TEXT,
                  rating REAL,
                  available INTEGER,
                  password TEXT)''')
    
    # Create Appointments table
    c.execute('''CREATE TABLE IF NOT EXISTS appointments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  customer_id INTEGER,
                  technician_id INTEGER,
                  service_tag TEXT,
                  issue_description TEXT,
                  appointment_date TEXT,
                  appointment_time TEXT,
                  status TEXT,
                  FOREIGN KEY (customer_id) REFERENCES customers (id),
                  FOREIGN KEY (technician_id) REFERENCES technicians (id))''')
    
    # Insert sample data if tables are empty
    if c.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        sample_customers = [
            ("ABC123", "John Doe", "vaishnavi.m@ubtiinc.com", "555-1001", "123 Main St, New York", 
             "Dell XPS 15", "2023-01-15", "2025-12-31", 1),
            ("XYZ789", "Jane Smith", "vaishnavi.m@ubtiinc.com", "555-1002", "456 Oak Ave, Chicago", 
             "HP Spectre x360", "2022-06-30", "2023-06-30", 0),
            ("DEF456", "Mike Johnson", "vaishnavi.m@ubtiinc.com", "555-1003", "789 Pine Rd, Los Angeles", 
             "Lenovo ThinkPad X1", "2024-02-20", "2026-02-20", 1)
        ]
        c.executemany('''INSERT INTO customers 
                         (service_tag, customer_name, customer_email, customer_phone, 
                          customer_address, laptop_model, purchase_date, warranty_end_date, warranty_valid)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', sample_customers)
    
    if c.execute("SELECT COUNT(*) FROM technicians").fetchone()[0] == 0:
        sample_technicians = [
            ("Alex Chen", "vaishnavi.m@ubtiinc.com", "555-2001", "Dell", "Downtown", 4.8, 1, "tech123"),
            ("Sarah Williams", "vaishnavi.m@ubtiinc.com", "555-2002", "HP", "Midtown", 4.6, 1, "tech123"),
            ("David Kim", "vaishnavi.m@ubtiinc.com", "555-2003", "Lenovo", "Uptown", 4.9, 1, "tech123"),
            ("Priya Patel", "vaishnavi.m@ubtiinc.com", "555-2004", "Dell", "Suburb", 4.7, 1, "tech123"),
            ("James Wilson", "vaishnavi.m@ubtiinc.com", "555-2005", "HP", "City Center", 4.5, 1, "tech123")
        ]
        c.executemany('''INSERT INTO technicians 
                         (name, email, phone, specialization, location, rating, available, password)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', sample_technicians)
    
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Email functions
def send_email(to_email, subject, body):
    """Send email using SMTP"""
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        sender_email = os.getenv("SMTP_USER")
        sender_password = os.getenv("SMTP_PASSWORD")
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background-color: #f5f5f5; padding: 20px;">
                    <div style="background-color: white; border-radius: 5px; padding: 20px; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #4a6fa5;">Hardware Support Notification</h2>
                        <div style="margin: 15px 0;">
                            {body}
                        </div>
                        <p style="color: #666; font-size: 12px;">
                            This is an automated message. Please do not reply directly.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        print(f"Error: {str(e)}")  # Print the error for debugging
        return False


# Web scraping functions
# Function to extract phone numbers from text
def extract_phone(snippet):
    # Implement your phone extraction logic here
    return "Phone number"

def scrape_service_centers(brand, location):
    """Scrape service centers using Serper API"""
    try:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            st.error("API key for Serper is not set.")
            return []
        
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        data = {
            'q': f'{brand} authorized service centers in {location}, India',
            'gl': 'in',  # Set geolocation to India
            'hl': 'en'
        }
        
        response = requests.post(
            'https://google.serper.dev/search',
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            st.error(f"Failed to fetch data from the API. Status code: {response.status_code}")
            return []
        
        results = response.json().get('organic', [])
        service_centers = []
        
        for result in results:
            address = result.get('snippet', '').split('·')[0].strip()
            # Check if the location is in the address
            if location.lower() in address.lower():
                service_centers.append({
                    'name': result.get('title', ''),
                    'address': address,
                    'phone': extract_phone(result.get('snippet', '')),
                    'link': result.get('link', '')
                })
        
        # Limit to the first 3 results
        return service_centers[:3]
    except Exception as e:
        st.error(f"Scraping failed: {str(e)}")
        return []

# Core application functions
def analyze_image_for_defects(image_bytes):
    """Analyze the uploaded image for hardware defects using LLaMA Vision"""
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this image of a computer/laptop hardware component. 
                        Identify any visible defects such as cracks, burns, liquid damage, or other physical issues.
                        Provide a concise report with:
                        1. Defect detected (Yes/No)
                        2. Type of defect if present
                        3. Severity (Low/Medium/High)
                        4. Likely affected components
                        Respond in JSON format with these keys: defect_detected, defect_type, severity, affected_components"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Error analyzing image: {str(e)}")
        return None
        
def get_customer_by_service_tag(service_tag):
    """Retrieve customer details from database using service tag"""
    conn = sqlite3.connect('hardware_support.db')
    c = conn.cursor()
    c.execute("SELECT * FROM customers WHERE service_tag=?", (service_tag,))
    customer = c.fetchone()
    conn.close()
    
    if customer:
        columns = ['id', 'service_tag', 'customer_name', 'customer_email', 'customer_phone', 
                  'customer_address', 'laptop_model', 'purchase_date', 'warranty_end_date', 'warranty_valid']
        return dict(zip(columns, customer))
    return None

def get_available_technicians(brand):
    """Get available technicians specializing in the given brand"""
    conn = sqlite3.connect('hardware_support.db')
    c = conn.cursor()
    c.execute("SELECT * FROM technicians WHERE specialization=? AND available=1", (brand,))
    technicians = c.fetchall()
    conn.close()
    
    if technicians:
        columns = ['id', 'name', 'email', 'phone', 'specialization', 'location', 'rating', 'available', 'password']
        return [dict(zip(columns, tech)) for tech in technicians]
    return []

def schedule_appointment(customer_id, technician_id, service_tag, issue_description, appointment_datetime):
    """Schedule an appointment in the database"""
    conn = sqlite3.connect('hardware_support.db')
    c = conn.cursor()
    
    appointment_date = appointment_datetime.strftime("%Y-%m-%d")
    appointment_time = appointment_datetime.strftime("%H:%M")
    
    c.execute('''INSERT INTO appointments 
                 (customer_id, technician_id, service_tag, issue_description, 
                  appointment_date, appointment_time, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (customer_id, technician_id, service_tag, issue_description, 
               appointment_date, appointment_time, "Scheduled"))
    
    conn.commit()
    appointment_id = c.lastrowid
    conn.close()
    
    return appointment_id

def get_warranty_renewal_info(brand):
    """Get warranty renewal information for a specific brand"""
    renewal_info = {
        "Dell": {
            "steps": [
                "Visit Dell's warranty extension website",
                "Enter your service tag to check eligibility",
                "Select your preferred extension period (1-3 years)",
                "Make payment online",
                "Receive confirmation email with updated warranty details"
            ],
            "link": "https://www.dell.com/support/contractservices/en-in",
            "pricing": "Starting at $99/year for basic coverage"
        },
        "HP": {
            "steps": [
                "Go to HP Care Pack purchase page",
                "Enter your product number or select your model",
                "Choose your Care Pack option",
                "Complete the purchase",
                "Your warranty will be automatically updated"
            ],
            "link": "https://www.hp.com/in-en/shop/carepack/warranty.html",
            "pricing": "Starting at $129/year for basic coverage"
        },
        "Lenovo": {
            "steps": [
                "Visit Lenovo's warranty upgrade site",
                "Enter your serial number",
                "Select your upgrade options",
                "Proceed to checkout",
                "Your warranty status will update within 24 hours"
            ],
            "link": "https://pcsupport.lenovo.com/in/en/warranty-lookup#/",
            "pricing": "Starting at $89/year for basic coverage"
        }
    }
    return renewal_info.get(brand, {})

# Streamlit UI
def main():
    st.set_page_config(
        page_title="Automated Hardware Support Agent",
        page_icon="🛠️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    :root {
        --primary: #4a6fa5;
        --secondary: #166088;
        --accent: #4fc3f7;
        --success: #4caf50;
        --warning: #ff9800;
        --danger: #f44336;
        --light: #f8f9fa;
        --dark: #212529;
    }
    
    .main {
        background-color: #f5f5f5;
    }
    .stApp {
        max-width: 1400px;
        margin: 0 auto;
    }
    .header {
        color: var(--secondary);
        padding: 1rem 0;
        border-bottom: 2px solid var(--accent);
        margin-bottom: 2rem;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: transform 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .success-card {
        border-left: 5px solid var(--success);
    }
    .warning-card {
        border-left: 5px solid var(--warning);
    }
    .info-card {
        border-left: 5px solid var(--accent);
    }
    .danger-card {
        border-left: 5px solid var(--danger);
    }
    .technician-card {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .technician-avatar {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background-color: var(--accent);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 1.5rem;
    }
    .technician-details {
        flex-grow: 1;
    }
    .rating {
        color: #FFD700;
        font-size: 1.2rem;
    }
    .service-center-card {
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .progress-container {
        width: 100%;
        background-color: #e0e0e0;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .progress-bar {
        height: 10px;
        border-radius: 5px;
        background-color: var(--primary);
    }
    .step {
        display: flex;
        margin-bottom: 1rem;
        align-items: center;
    }
    .step-number {
        background-color: var(--primary);
        color: white;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 1rem;
        flex-shrink: 0;
    }
    .step-content {
        flex-grow: 1;
    }
    .defect-image {
        max-width: 100%;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .btn-primary {
        background-color: var(--primary) !important;
        color: white !important;
        border: none !important;
    }
    .btn-primary:hover {
        background-color: var(--secondary) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://img.freepik.com/premium-vector/repair-service-computer-equipment-laptops-gadgets_261524-807.jpg", use_container_width=True)
        st.markdown("## Navigation")
        nav_option = st.radio("", ["Home", "Customer Support", "Technician Portal", "Admin Dashboard"])
        
        st.markdown("---")
        st.markdown("### Need Help?")
        st.markdown("📞 Call: 1-800-SUPPORT")
        st.markdown("✉️ Email: support@example.com")
    
    # Initialize session state
    if 'defect_analysis' not in st.session_state:
        st.session_state.defect_analysis = None
    if 'customer_info' not in st.session_state:
        st.session_state.customer_info = None
    if 'technician_selected' not in st.session_state:
        st.session_state.technician_selected = None
    if 'appointment_scheduled' not in st.session_state:
        st.session_state.appointment_scheduled = None
    if 'address_updated' not in st.session_state:
        st.session_state.address_updated = False
    
    # Home Page
    if nav_option == "Home":
        st.title("🛠️ Automated Hardware Support Agent")
        st.markdown("""
        <div class="card info-card">
            <h3>Welcome to our Hardware Support Portal</h3>
            <p>Upload an image of your defective hardware, and our AI agent will analyze it, 
            verify your warranty, and help schedule a repair appointment.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div class="card">
                <h4>🔍 Defect Analysis</h4>
                <p>Our AI will analyze images of your hardware to identify defects and issues.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="card">
                <h4>📅 Appointment Scheduling</h4>
                <p>Book a technician visit at your preferred date and time.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="card">
                <h4>🛡️ Warranty Services</h4>
                <p>Check your warranty status and get support options.</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("## How It Works")
        
        steps = [
            {"number": 1, "title": "Upload Image", "description": "Take a clear photo of the defective hardware component."},
            {"number": 2, "title": "AI Analysis", "description": "Our system will analyze the image for defects and issues."},
            {"number": 3, "title": "Verify Details", "description": "Enter your service tag to check warranty status."},
            {"number": 4, "title": "Get Support", "description": "Schedule a repair or find service centers near you."}
        ]
        
        for step in steps:
            with st.container():
                st.markdown(f"""
                <div class="step">
                    <div class="step-number">{step['number']}</div>
                    <div class="step-content">
                        <h4>{step['title']}</h4>
                        <p>{step['description']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Customer Support Portal
    elif nav_option == "Customer Support":
        st.title("Customer Support Portal")
        
        # Progress bar
        progress = st.empty()
        progress_bar = 25 if not st.session_state.defect_analysis else \
                       50 if st.session_state.defect_analysis and not st.session_state.customer_info else \
                       75 if st.session_state.customer_info and not st.session_state.appointment_scheduled else 100
        
        progress.markdown(f"""
        <div class="progress-container">
            <div class="progress-bar" style="width: {progress_bar}%"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 5px;">
            <span>Step 1: Defect Analysis</span>
            <span>Step 2: Verify Details</span>
            <span>Step 3: Schedule</span>
            <span>Step 4: Confirmation</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Step 1: Image Upload and Analysis
        st.header("Step 1: Upload Image of Defective Hardware")
        uploaded_file = st.file_uploader(
            "Upload a clear image of the defective component", 
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=False,
            key="file_uploader"
        )
        
        if uploaded_file is not None:
            image_bytes = uploaded_file.read()
            image = Image.open(io.BytesIO(image_bytes))
            
            col1, col2 = st.columns(2)
            with col1:
                st.image(image, caption="Uploaded Image", use_container_width=True, output_format="JPEG")
            
            with col2:
                if st.button("Analyze Image for Defects", key="analyze_btn"):
                    with st.spinner("Analyzing image for defects..."):
                        st.session_state.defect_analysis = analyze_image_for_defects(image_bytes)
                        time.sleep(1)
                    
                    if st.session_state.defect_analysis:
                        if st.session_state.defect_analysis.get('defect_detected', False):
                            st.markdown(f"""
                            <div class="card danger-card">
                                <h3>Defect Detected!</h3>
                                <p><strong>Type:</strong> {st.session_state.defect_analysis.get('defect_type', 'Unknown')}</p>
                                <p><strong>Severity:</strong> <span style="color: {'green' if st.session_state.defect_analysis.get('severity') == 'Low' else 'orange' if st.session_state.defect_analysis.get('severity') == 'Medium' else 'red'}">{st.session_state.defect_analysis.get('severity', 'Unknown')}</span></p>
                                <p><strong>Affected Components:</strong> {st.session_state.defect_analysis.get('affected_components', 'Not specified')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                            <div class="card success-card">
                                <h3>✅ No Defects Detected</h3>
                                <p>Our analysis didn't find any visible defects in your image.</p>
                                <p>If you're still experiencing issues, please contact our support team for further assistance.</p>
                            </div>
                            """, unsafe_allow_html=True)
        
        # Step 2: Service Tag Verification
        if st.session_state.defect_analysis and st.session_state.defect_analysis.get('defect_detected', False):
            st.header("Step 2: Verify Service Tag & Customer Details")
            service_tag = st.text_input("Enter your service tag number (found on the bottom of your device):", key="service_tag_input")
            
            if st.button("Verify Service Tag", key="verify_btn"):
                st.session_state.customer_info = get_customer_by_service_tag(service_tag)
                
                if st.session_state.customer_info:
                    st.markdown(f"""
                    <div class="card success-card">
                        <h3>✅ Customer Verified</h3>
                        <p><strong>Name:</strong> {st.session_state.customer_info['customer_name']}</p>
                        <p><strong>Email:</strong> {st.session_state.customer_info['customer_email']}</p>
                        <p><strong>Phone:</strong> {st.session_state.customer_info['customer_phone']}</p>
                        <p><strong>Model:</strong> {st.session_state.customer_info['laptop_model']}</p>
                        <p><strong>Purchase Date:</strong> {st.session_state.customer_info['purchase_date']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if not st.session_state.customer_info['customer_address'] or len(st.session_state.customer_info['customer_address']) < 5:
                        st.warning("Please update your address details for service scheduling.")
                        new_address = st.text_area("Enter your complete address:", key="address_input")
                        if st.button("Update Address", key="update_address_btn"):
                            if new_address:
                                conn = sqlite3.connect('hardware_support.db')
                                c = conn.cursor()
                                c.execute("UPDATE customers SET customer_address=? WHERE id=?", 
                                          (new_address, st.session_state.customer_info['id']))
                                conn.commit()
                                conn.close()
                                st.session_state.customer_info['customer_address'] = new_address
                                st.session_state.address_updated = True
                                st.success("Address updated successfully!")
                            else:
                                st.error("Please enter a valid address")
                    else:
                        st.session_state.address_updated = True
                else:
                    st.markdown("""
                    <div class="card danger-card">
                        <h3>❌ Service Tag Not Found</h3>
                        <p>We couldn't find your service tag in our database. Please check the number and try again.</p>
                        <p>If you believe this is an error, please contact our support team.</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Step 3: Warranty Check and Service Options
        if st.session_state.customer_info and st.session_state.address_updated:
            st.header("Step 3: Warranty & Service Options")
            
            brand = None
            if "dell" in st.session_state.customer_info['laptop_model'].lower():
                brand = "Dell"
            elif "hp" in st.session_state.customer_info['laptop_model'].lower():
                brand = "HP"
            elif "lenovo" in st.session_state.customer_info['laptop_model'].lower():
                brand = "Lenovo"
            
            if st.session_state.customer_info['warranty_valid']:
                st.markdown(f"""
                <div class="card success-card">
                    <h3>✅ Warranty Active</h3>
                    <p>Your device is covered under warranty until <strong>{st.session_state.customer_info['warranty_end_date']}</strong>.</p>
                    <p>You're eligible for free at-home service for this issue.</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.subheader("Available Service Technicians")
                technicians = get_available_technicians(brand)
                
                if technicians:
                    if len(technicians) > 1:
                        tech_options = {f"{tech['name']} ({tech['location']}) - ★{tech['rating']}": tech['id'] for tech in technicians}
                        selected_tech = st.selectbox("Choose a technician:", options=list(tech_options.keys()))
                        st.session_state.technician_selected = tech_options[selected_tech]
                    else:
                        st.session_state.technician_selected = technicians[0]['id']
                    
                    selected_tech_details = next((tech for tech in technicians if tech['id'] == st.session_state.technician_selected), None)
                    
                    if selected_tech_details:
                        initials = "".join([name[0] for name in selected_tech_details['name'].split()[:2]]).upper()
                        st.markdown(f"""
                        <div class="card info-card">
                            <div class="technician-card">
                                <div class="technician-avatar">{initials}</div>
                                <div class="technician-details">
                                    <h4>{selected_tech_details['name']}</h4>
                                    <p>📞 {selected_tech_details['phone']}</p>
                                    <p>📍 {selected_tech_details['location']}</p>
                                    <div class="rating">{"★" * int(selected_tech_details['rating'])}</div>
                                </div>
                            </div>
                            <p><strong>Specialization:</strong> {selected_tech_details['specialization']}</p>
                            <p>This technician is available for at-home service in your area.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.subheader("Schedule Your Appointment")
                        appointment_date = st.date_input("Preferred date:", min_value=datetime.today(), 
                                                       max_value=datetime.today() + timedelta(days=30))
                        appointment_time = st.time_input("Preferred time:", 
                                                         value=datetime.strptime("10:00", "%H:%M").time())
                        
                        issue_description = st.text_area("Describe the issue in more detail:", 
                                                        value=st.session_state.defect_analysis.get('defect_type', ""))
                        
                        if st.button("Confirm Appointment", key="schedule_btn"):
                            appointment_datetime = datetime.combine(appointment_date, appointment_time)
                            appointment_id = schedule_appointment(
                                st.session_state.customer_info['id'],
                                st.session_state.technician_selected,
                                st.session_state.customer_info['service_tag'],
                                issue_description,
                                appointment_datetime
                            )
                            
                            # Send confirmation email
                            email_body = f"""
                            <p>Your appointment has been scheduled successfully!</p>
                            <p><strong>Details:</strong></p>
                            <ul>
                                <li>Date: {appointment_date.strftime('%B %d, %Y')}</li>
                                <li>Time: {appointment_time.strftime('%I:%M %p')}</li>
                                <li>Technician: {selected_tech_details['name']}</li>
                                <li>Contact: {selected_tech_details['phone']}</li>
                                <li>Address: {st.session_state.customer_info['customer_address']}</li>
                            </ul>
                            <p>Our technician will call you before the scheduled visit.</p>
                            """
                            send_email(st.session_state.customer_info['customer_email'], 
                                     "Appointment Confirmation", email_body)
                            
                            st.session_state.appointment_scheduled = {
                                "id": appointment_id,
                                "date": appointment_date.strftime("%B %d, %Y"),
                                "time": appointment_time.strftime("%I:%M %p"),
                                "technician": selected_tech_details['name'],
                                "phone": selected_tech_details['phone']
                            }
                            
                            st.rerun()
                else:
                    st.warning("No technicians available for your brand at this time.")
                    st.info("Please try again later or contact our support team for assistance.")
            else:
                st.markdown(f"""
                <div class="card warning-card">
                    <h3>⚠️ Warranty Expired</h3>
                    <p>Your warranty ended on <strong>{st.session_state.customer_info['warranty_end_date']}</strong>.</p>
                    <p>You can either:</p>
                    <ol>
                        <li>Renew your warranty (if eligible)</li>
                        <li>Use our paid repair services</li>
                        <li>Visit an authorized service center</li>
                    </ol>
                </div>
                """, unsafe_allow_html=True)
                
                if brand:
                    renewal_info = get_warranty_renewal_info(brand)
                    if renewal_info:
                        st.subheader("Warranty Renewal Options")
                        st.markdown(f"""
                        <div class="card info-card">
                            <h4>Renew {brand} Warranty</h4>
                            <p><strong>Pricing:</strong> {renewal_info['pricing']}</p>
                            <p><strong>Steps to renew:</strong></p>
                            <ol>
                                {"".join([f"<li>{step}</li>" for step in renewal_info['steps']])}
                            </ol>
                            <p><a href="{renewal_info['link']}" target="_blank">Visit {brand} Warranty Renewal Page</a></p>
                        </div>
                        """, unsafe_allow_html=True)
                
                        # Ask the user for their location
                        location = st.text_input("Enter your location (city or zip code):")

                        if st.button("Find Service Centers"):
                            if location:
                                # Call the scrape_service_centers function with both brand and location
                                service_centers = scrape_service_centers(brand, location)
                                if service_centers:
                                    for center in service_centers:
                                        st.markdown(f"""
                                        <div class="card service-center-card">
                                            <h4>{center['name']}</h4>
                                            <p>📍 <strong>Address:</strong> {center['address']}</p>
                                            <p>📞 <strong>Phone:</strong> {center['phone']}</p>
                                            <p><a href="{center['link']}" target="_blank">View Details</a></p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.warning("No service centers found for this brand in the specified location.")
                            else:
                                st.error("Please enter a valid location.")
        
        # Step 4: Appointment Confirmation
        if st.session_state.appointment_scheduled:
            st.header("Step 4: Appointment Confirmation")
            st.markdown(f"""
            <div class="card success-card">
                <h3>✅ Appointment Scheduled Successfully!</h3>
                <p><strong>Appointment ID:</strong> {st.session_state.appointment_scheduled['id']}</p>
                <p><strong>Date:</strong> {st.session_state.appointment_scheduled['date']}</p>
                <p><strong>Time:</strong> {st.session_state.appointment_scheduled['time']}</p>
                <p><strong>Technician:</strong> {st.session_state.appointment_scheduled['technician']}</p>
                <p><strong>Contact:</strong> {st.session_state.appointment_scheduled['phone']}</p>
                <p><strong>Address:</strong> {st.session_state.customer_info['customer_address']}</p>
                <p>A confirmation has been sent to <strong>{st.session_state.customer_info['customer_email']}</strong>.</p>
                <p>Our technician will call you before the scheduled visit.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Schedule Another Appointment", key="new_appointment_btn"):
                st.session_state.defect_analysis = None
                st.session_state.customer_info = None
                st.session_state.technician_selected = None
                st.session_state.appointment_scheduled = None
                st.session_state.address_updated = False
                st.rerun()
    
    # Technician Portal
    elif nav_option == "Technician Portal":
        st.title("👨‍🔧 Technician Portal")
        
        tech_id = st.text_input("Enter Technician ID:")
        tech_pass = st.text_input("Password:", type="password")
        
        conn = sqlite3.connect('hardware_support.db')
        technician = conn.execute(
            "SELECT * FROM technicians WHERE id=? AND password=?", 
            (tech_id, tech_pass)
        ).fetchone()
        
        if not technician:
            
            st.stop()
        
        columns = ['id', 'name', 'email', 'phone', 'specialization', 'location', 'rating', 'available', 'password']
        technician = dict(zip(columns, technician))
        
        st.success(f"Welcome, {technician['name']}!")
        
        st.header("Your Schedule")
        appointments = pd.read_sql(f"""
            SELECT a.id, c.customer_name, c.customer_phone, c.customer_address,
                   a.service_tag, a.issue_description, 
                   a.appointment_date, a.appointment_time, a.status
            FROM appointments a
            JOIN customers c ON a.customer_id = c.id
            WHERE a.technician_id = {technician['id']}
            AND a.appointment_date >= date('now')
            ORDER BY a.appointment_date
        """, conn)
        
        if not appointments.empty:
            for _, appt in appointments.iterrows():
                with st.expander(f"{appt['appointment_date']} - {appt['customer_name']} ({appt['status']})"):
                    st.markdown(f"""
                    Customer: {appt['customer_name']}  
                    Phone: {appt['customer_phone']}  
                    Address: {appt['customer_address']}  
                    Service Tag: {appt['service_tag']}  
                    Issue: {appt['issue_description']}
                    """)
                    
                    cols = st.columns(3)
                    with cols[0]:
                        if st.button("Start Service", key=f"start_{appt['id']}"):
                            conn.execute("UPDATE appointments SET status='In Progress' WHERE id=?", (appt['id'],))
                            conn.commit()
                            st.rerun()
                    with cols[1]:
                        if st.button("Complete", key=f"complete_{appt['id']}"):
                            conn.execute("UPDATE appointments SET status='Completed' WHERE id=?", (appt['id'],))
                            conn.commit()
                            
                            # Send completion email
                            customer_email = conn.execute(
                                "SELECT customer_email FROM customers WHERE id=?", 
                                (appt['customer_id'],)
                            ).fetchone()[0]
                            
                            email_body = f"""
                            <p>Your service appointment has been completed!</p>
                            <p><strong>Details:</strong></p>
                            <ul>
                                <li>Technician: {technician['name']}</li>
                                <li>Service Tag: {appt['service_tag']}</li>
                                <li>Issue: {appt['issue_description']}</li>
                            </ul>
                            <p>Please contact us if you have any questions about your repair.</p>
                            """
                            send_email(customer_email, "Service Completed", email_body)
                            st.rerun()
        else:
            st.info("No upcoming appointments")
        
        conn.close()
    
    # Admin Dashboard
    elif nav_option == "Admin Dashboard":
        st.title("🔒 Admin Dashboard")
        
        admin_pass = st.text_input("Enter Admin Password:", type="password")
        if admin_pass != os.getenv("ADMIN_PASSWORD", "admin123"):

            st.stop()
        
        tab1, tab2, tab3 = st.tabs(["Customers", "Technicians", "Appointments"])
        
        with tab1:
            st.header("Customer Management")
            conn = sqlite3.connect('hardware_support.db')
            customers = pd.read_sql("SELECT * FROM customers", conn)
            st.dataframe(customers)
            
            with st.expander("Add New Customer"):
                with st.form("add_customer"):
                    service_tag = st.text_input("Service Tag")
                    name = st.text_input("Name")
                    email = st.text_input("Email")
                    phone = st.text_input("Phone")
                    address = st.text_area("Address")
                    model = st.text_input("Laptop Model")
                    purchase_date = st.date_input("Purchase Date")
                    warranty_end = st.date_input("Warranty End Date")
                    warranty_valid = st.checkbox("Warranty Active")
                    
                    if st.form_submit_button("Add Customer"):
                        try:
                            conn.execute('''INSERT INTO customers 
                                         (service_tag, customer_name, customer_email, customer_phone,
                                          customer_address, laptop_model, purchase_date, warranty_end_date, warranty_valid)
                                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                      (service_tag, name, email, phone, address, model, 
                                       purchase_date.strftime("%Y-%m-%d"), warranty_end.strftime("%Y-%m-%d"), 
                                       int(warranty_valid)))
                            conn.commit()
                            st.success("Customer added!")
                        except sqlite3.IntegrityError:
                            st.error("Service tag already exists")
            
            with st.expander("Delete Customer"):
                customer_id = st.text_input("Enter Customer ID to delete:")
                if st.button("Delete Customer"):
                    conn.execute("DELETE FROM customers WHERE id=?", (customer_id,))
                    conn.commit()
                    st.success("Customer deleted")
        
        with tab2:
            st.header("Technician Management")
            technicians = pd.read_sql("SELECT id, name, specialization, location, rating, available FROM technicians", conn)
            st.dataframe(technicians)
            
            with st.expander("Add New Technician"):
                with st.form("add_technician"):
                    name = st.text_input("Name")
                    email = st.text_input("Email")
                    phone = st.text_input("Phone")
                    specialization = st.selectbox("Specialization", ["Dell", "HP", "Lenovo"])
                    location = st.text_input("Location")
                    rating = st.slider("Rating", 1.0, 5.0, 4.5)
                    available = st.checkbox("Available", value=True)
                    password = st.text_input("Password", type="password")
                    
                    if st.form_submit_button("Add Technician"):
                        conn.execute('''INSERT INTO technicians 
                                     (name, email, phone, specialization, location, rating, available, password)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                                  (name, email, phone, specialization, location, rating, int(available), password))
                        conn.commit()
                        st.success("Technician added!")
        
        with tab3:
            st.header("Appointment Monitoring")
            appointments = pd.read_sql("""
                SELECT a.id, c.customer_name, t.name as technician, 
                       a.appointment_date, a.appointment_time, a.status
                FROM appointments a
                JOIN customers c ON a.customer_id = c.id
                JOIN technicians t ON a.technician_id = t.id
                ORDER BY a.appointment_date
            """, conn)
            st.dataframe(appointments)
            
            st.subheader("Update Appointment Status")
            selected_id = st.selectbox("Select Appointment", appointments['id'])
            new_status = st.selectbox("New Status", 
                                    ["Scheduled", "In Progress", "Completed", "Cancelled"])
            if st.button("Update Status"):
                conn.execute("UPDATE appointments SET status=? WHERE id=?", 
                            (new_status, selected_id))
                conn.commit()
                st.success("Status updated!")
        
        conn.close()

if __name__ == "__main__":
    main()
