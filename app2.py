import streamlit as st
import nltk
import spacy
import pandas as pd
import base64
import random
import time
import datetime
import os
import pymysql
from pyresparser import ResumeParser
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io
from streamlit_tags import st_tags
from PIL import Image
import plotly.express as px

# Download necessary NLTK data
nltk.download('stopwords')

# Load Spacy model
spacy.load('en_core_web_sm')

# Import courses module
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos

# Database Connection
def create_db_connection():
    try:
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='chinujain',
            database='sra'
        )
        return connection
    except pymysql.Error as e:
        st.error(f"Error connecting to MySQL database: {e}")
        return None

connection = create_db_connection()
if connection:
    cursor = connection.cursor()

# Utility Functions
def get_table_download_link(df, filename, text):
    """Generates a link allowing the data in a given pandas dataframe to be downloaded."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'

def pdf_reader(file):
    """Extracts text from PDF file using pdfminer."""
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
        text = fake_file_handle.getvalue()

    converter.close()
    fake_file_handle.close()
    return text

def show_pdf(file_path):
    """Displays PDF in Streamlit app."""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# Resume Parsing and Analysis
def analyze_resume(file):
    """Analyze the resume and return the extracted data."""
    save_image_path = './Uploaded_Resumes/' + file.name
    os.makedirs(os.path.dirname(save_image_path), exist_ok=True)

    with open(save_image_path, "wb") as f:
        f.write(file.getbuffer())

    show_pdf(save_image_path)
    return ResumeParser(save_image_path).get_extracted_data(), save_image_path

# Course Recommendations
def course_recommender(course_list):
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    for c, (c_name, c_link) in enumerate(course_list):
        if c == no_of_reco:
            break
        st.markdown(f"({c+1}) [{c_name}]({c_link})")
        rec_course.append(c_name)
    return rec_course

# Database Functions
def create_user_table():
    """Create table for storing user data if not exists."""
    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS sra;")
        cursor.execute("USE sra;")

        table_sql = """
            CREATE TABLE IF NOT EXISTS resume_data (
                ID INT NOT NULL AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(50) NOT NULL,
                resume_score VARCHAR(8) NOT NULL,
                timestamp VARCHAR(50) NOT NULL,
                no_of_pages VARCHAR(5) NOT NULL,
                reco_field VARCHAR(25) NOT NULL,
                user_level VARCHAR(30) NOT NULL,
                skills VARCHAR(300) NOT NULL,
                Recommended_skills VARCHAR(300) NOT NULL,
                Recommended_courses VARCHAR(600) NOT NULL,
                PRIMARY KEY (ID)
            );
        """
        cursor.execute(table_sql)
        connection.commit()
    except pymysql.Error as e:
        st.error(f"Error creating table: {e}")

def insert_data(name, email, resume_score, timestamp, no_of_pages, reco_field, candidate_level, skills, recommended_skills, rec_course):
    """Insert data into the resume_data table."""
    try:
        insert_sql = """INSERT INTO resume_data (name, email, resume_score, timestamp, no_of_pages, reco_field, candidate_level, skills, Recommended_skills, Recommended_courses)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        rec_values = (name, email, resume_score, timestamp, no_of_pages, reco_field, candidate_level, str(skills), str(recommended_skills), str(rec_course))

        cursor.execute(insert_sql, rec_values)
        connection.commit()
        st.success("Your resume data has been stored successfully!")
    except pymysql.Error as e:
        st.error(f"Error inserting data: {e}")
        connection.rollback()

# Video Functions - UPDATED WITH FIXES
def display_video_tips():
    """Display resume writing and interview preparation videos with robust error handling."""
    try:
        # Resume Writing Tips Video
        st.header("**Bonus Video for Resume Writing Tips💡**")
        if resume_videos:  # Check if list is not empty
            resume_vid = random.choice(resume_videos)
            st.video(resume_vid)
        else:
            st.warning("No resume videos available")

        # Interview Tips Video
        st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
        if interview_videos:  # Check if list is not empty
            interview_vid = random.choice(interview_videos)
            st.video(interview_vid)
        else:
            st.warning("No interview videos available")

    except Exception as e:
        st.warning(f"Couldn't load video tips: {str(e)}")

def calculate_resume_score(resume_data, reco_field, recommended_skills):
    """Calculates a resume score based on the extracted data and recommendations."""
    score = 0

    # Check for basic information
    if resume_data.get('name'):
        score += 10
    if resume_data.get('email'):
        score += 10
    if resume_data.get('mobile_number'):
        score += 10
    if resume_data.get('education'):
        score += 15
    if resume_data.get('experience'):
        score += 20
    if resume_data.get('skills'):
        score += 15

    # Check for keyword matching with recommended skills
    extracted_skills = [skill.lower() for skill in resume_data.get('skills', [])]
    matched_skills = 0
    for recommended_skill in [skill.lower() for skill in recommended_skills]:
        if recommended_skill in extracted_skills:
            matched_skills += 5
    score += matched_skills

    # Consider number of pages
    if resume_data.get('no_of_pages', 1) <= 2:
        score += 10
    elif resume_data.get('no_of_pages', 1) > 3:
        score -= 5

    return min(100, score)

# Main Application Functions
def handle_normal_user():
    """Handle normal user flow: Upload resume and analyze it."""
    pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])

    if pdf_file:
        resume_data, save_image_path = analyze_resume(pdf_file)

        if resume_data:
            st.success(f"Hello {resume_data.get('name')}")

            # Display basic info
            st.subheader("**Your Basic info**")
            try:
                st.text(f"Name: {resume_data['name']}")
                st.text(f"Email: {resume_data['email']}")
                st.text(f"Contact: {resume_data['mobile_number']}")
                st.text(f"Resume pages: {str(resume_data['no_of_pages'])}")
            except KeyError:
                st.warning("Could not extract all basic information from the resume")

            # Calculate resume score
            recommended_skills, reco_field, rec_course = analyze_skills(resume_data)
            resume_score = calculate_resume_score(resume_data, reco_field, recommended_skills)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Define candidate's level
            experience = resume_data.get('experience', [])
            if experience is None or len(experience) == 0:
                candidate_level = "Beginner"
            elif len(experience) <= 3:
                candidate_level = "Intermediate"
            else:
                candidate_level = "Expert"

            # Skills analysis and recommendations
            st.subheader("**Skills Recommendation💡**")
            keywords = st_tags(label='### Skills that you have',
                                 text='See our skills recommendation',
                                 value=resume_data['skills'],
                                 key='1')

            st.success(f"** Recommended skills for {reco_field}: **")
            st_tags(label='### Recommended skills for you.',
                    value=recommended_skills,
                    key='2')

            course_recommender(rec_course)

            # Display resume score and tips
            st.subheader("**Resume Tips & Ideas💡**")
            st.success(f"** Your Resume Writing Score: {resume_score:.2f} **")
            st.warning("** Note: This score is based on the content of your resume. **")
            st.progress(resume_score / 100.0 if resume_score <= 100 else 1.0)

            # Insert the data into the database
            insert_data(
                resume_data['name'],
                resume_data['email'],
                resume_score,
                timestamp,
                resume_data['no_of_pages'],
                reco_field,
                candidate_level,
                resume_data['skills'],
                recommended_skills,
                rec_course
            )

            # Display video tips
            display_video_tips()
        else:
            st.error('Failed to parse resume.')

def analyze_skills(resume_data):
    """Analyze the skills in the resume and return recommendations."""
    skills = resume_data.get("skills", [])
    recommended_skills = []
    reco_field = "Unknown"
    rec_course = []

    if "python" in [s.lower() for s in skills]:
        recommended_skills = ["Machine Learning", "Data Science", "Artificial Intelligence"]
        reco_field = "Data Science"
        rec_course = ds_course
    elif "java" in [s.lower() for s in skills]:
        recommended_skills = ["Java Development", "Spring Framework", "Web Development"]
        reco_field = "Software Development"
        rec_course = android_course
    elif "web development" in [s.lower() for s in skills]:
        recommended_skills = ["HTML", "CSS", "JavaScript", "React", "Node.js"]
        reco_field = "Web Development"
        rec_course = web_course

    return recommended_skills, reco_field, rec_course

def handle_admin():
    """Admin panel to view and download user data."""
    st.success('Welcome to Admin Side')
    ad_user = st.text_input("Username")
    ad_password = st.text_input("Password", type='password')
    if st.button('Login'):
        if ad_user == 'Amigoes' and ad_password == 'Amigoes':
            st.success("Welcome Admin")
            try:
                cursor.execute("SELECT * FROM resume_data")
                data = cursor.fetchall()
                if data:
                    df = pd.DataFrame(data, columns=['ID', 'Name', 'Email', 'Resume Score', 'Timestamp',
                                                     'Total Page', 'Predicted Field', 'User Level',
                                                     'skills', 'Recommended Skills', 'Recommended Course'])
                    st.dataframe(df)
                    st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)

                    # Plot Pie charts
                    st.subheader("📈 Pie Chart for Predicted Field Recommendations")
                    fig = px.pie(df, values=df['Predicted Field'].value_counts(),
                                 names=df['Predicted Field'].unique(),
                                 title='Predicted Field')
                    st.plotly_chart(fig)

                    st.subheader("📈 Pie Chart for User Experience Level")
                    fig = px.pie(df, values=df['User Level'].value_counts(),
                                 names=df['User Level'].unique(),
                                 title="User Experience Level")
                    st.plotly_chart(fig)
                else:
                    st.warning("No data found in the database")
            except pymysql.Error as e:
                st.error(f"Error fetching data: {e}")
        else:
            st.error("Wrong ID & Password Provided")

# Main function to run the app
def run():
    st.set_page_config(page_title="Smart Resume Analyzer", page_icon='./Logo/SRA_Logo.ico')
    st.title("Smart Resume Analyser")

    # Initialize database connection and tables
    if connection:
        create_user_table()
    else:
        st.error("Could not connect to database. Some features may not work.")

    # Sidebar and navigation
    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)

    # Logo and branding
    img = Image.open('./Logo/SRA_Logo.jpg')
    img = img.resize((250, 250))
    st.image(img)

    if choice == 'Normal User':
        handle_normal_user()
    else:
        handle_admin()

# Run the Streamlit app
if __name__ == "__main__":
    run()