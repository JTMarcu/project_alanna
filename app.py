import os
import pandas as pd
import streamlit as st
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import subprocess

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="AI Resume & Cover Letter Generator", layout="centered")
st.title("📄 AI Resume Tuner + Cover Letter Generator")
st.markdown("Paste a job description below and get a customized resume + cover letter.")

# Create output directory
os.makedirs("output", exist_ok=True)

# === Section 1: Upload Resume CSV ===
df = None
csv_file = st.file_uploader("Upload your resume_data.csv", type="csv")

if csv_file:
    df = pd.read_csv(csv_file)

# === Section 2: Job Description Input ===
job_description = st.text_area("Paste the job description here:", height=300)

# === Section 3: Resume + Cover Letter Generator ===
if st.button("Generate Resume & Cover Letter") and job_description and df is not None:
    with st.spinner("Generating personalized documents..."):
        try:
            docs = [Document(page_content=row["content"], metadata=row.to_dict()) for _, row in df.iterrows()]
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            split_docs = splitter.split_documents(docs)

            embeddings = OpenAIEmbeddings()
            vectorstore = FAISS.from_documents(split_docs, embeddings)
            relevant_docs = vectorstore.similarity_search(job_description, k=8)
            relevant_experience = "\n".join([doc.page_content for doc in relevant_docs])

            st.write("🔄 Sending prompt to GPT...")
            llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
            prompt_template = PromptTemplate(
                input_variables=["job_description", "experience"],
                template="""
You are a job search assistant. A user is applying for the following role:

[Job Description]
{job_description}

Here is their background:
{experience}

1. Generate a tailored resume CSV based on their background and the job description.
   Use columns: section, subsection, content.
   Only include the most relevant skills, experience, and projects.

2. Also generate a personalized, concise cover letter.
                """
            )

            chain = LLMChain(llm=llm, prompt=prompt_template)
            response = chain.run({
                "job_description": job_description,
                "experience": relevant_experience
            })
            st.write("✅ Got response from GPT.")

            st.markdown("---")
            st.subheader("🧠 GPT Output Preview")
            st.code(response)

            csv_text, cover_letter = "", ""
            if "section," in response:
                csv_part = response.split("section,")[1].strip()
                csv_text = "section," + csv_part
            if "Dear" in response:
                letter_start = response.index("Dear")
                cover_letter = response[letter_start:]

            tailored_csv_path = os.path.join("output", "tailored_resume.csv")
            cover_letter_path = os.path.join("output", "cover_letter.txt")
            output_pdf = os.path.join("output", "tailored_resume.pdf")

            with open(tailored_csv_path, "w", encoding="utf-8") as f:
                f.write(csv_text)

            with open(cover_letter_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)

            subprocess.run(["python", "resume.py", tailored_csv_path, output_pdf])

            if os.path.exists(output_pdf) and os.path.getsize(output_pdf) > 0:
                st.success("🎉 Done! Download your documents below:")
                st.download_button("📄 Download Resume PDF", open(output_pdf, "rb"), file_name="tailored_resume.pdf")
                st.download_button("💌 Download Cover Letter", open(cover_letter_path, "rb"), file_name="cover_letter.txt")
            else:
                st.error("❌ Failed to generate resume PDF. Please check the CSV format or content.")

        except Exception as e:
            st.error(f"❌ An error occurred: {e}")

# === Section 4: Add New Entry to Master Resume CSV ===
st.markdown("---")
st.subheader("➕ Add New Content to Resume Data")

with st.form("add_entry_form"):
    section = st.selectbox("Section", ["professional_summary", "technical_skills", "professional_experience", "certifications", "projects"])
    subsection = st.text_input("Subsection (e.g. project name, role title)")
    content = st.text_area("Content (describe the experience, project, or skill)", height=150)
    submitted = st.form_submit_button("Add to Resume CSV")

    if submitted:
        if not csv_file:
            st.error("Please upload your resume_data.csv first.")
        else:
            new_row = pd.DataFrame([[section, subsection, content]], columns=["section", "subsection", "content"])
            df = pd.concat([df, new_row], ignore_index=True)

            updated_csv_path = os.path.join("output", "updated_resume_data.csv")
            df.to_csv(updated_csv_path, index=False)

            st.success("✅ New entry added!")
            st.download_button("⬇️ Download Updated CSV", open(updated_csv_path, "rb"), file_name="updated_resume_data.csv")
