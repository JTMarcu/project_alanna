# app.py
import os
import sys
import openai
import pandas as pd
import subprocess
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox

def get_job_description_from_dialog() -> str:
    """
    Opens a Tkinter window with a large text box for the user
    to paste or type the job description. Returns the result.
    """
    job_desc_container = []

    def on_ok():
        # Retrieve text from the box, store it, then close
        desc = text_box.get("1.0", "end-1c").strip()
        job_desc_container.append(desc)
        root.destroy()

    def on_cancel():
        root.destroy()

    root = tk.Tk()
    root.title("Job Description")

    label = tk.Label(root, text="Paste or type the job description below:")
    label.pack(padx=10, pady=5)

    text_box = tk.Text(root, wrap="word", width=80, height=20)
    text_box.pack(padx=10, pady=5)

    button_frame = tk.Frame(root)
    button_frame.pack(padx=10, pady=5)

    ok_button = tk.Button(button_frame, text="OK", command=on_ok)
    ok_button.pack(side="left", padx=5)

    cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
    cancel_button.pack(side="left", padx=5)

    root.mainloop()

    return job_desc_container[0] if job_desc_container else ""

def call_llm_to_shorten_resume(job_desc: str, full_resume_data: str) -> str:
    """
    Calls the OpenAI ChatCompletion to produce:
    - A short CSV for a 1-page resume
    - A cover letter
    in a single text output
    """
    prompt = f"""
You are a specialized AI that creates concise, ATS-friendly resumes for a job applicant.
IMPORTANT:
- Always include a personal_info section with subsections: name, target_roles, plus any relevant contact details.
=== JOB DESCRIPTION ===
{job_desc}

=== FULL RESUME DATA (CSV) ===
{full_resume_data}

YOUR TASK:
1) Produce a short CSV with columns (section,subsection,content), focusing on the most relevant details.
2) Follow that CSV with a concise cover letter (<=200 words),
   beginning with "Dear ".

Output format must be:
   section,subsection,content
   ... (CSV lines) ...
   Dear ...
   ... (cover letter) ...
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful resume-optimizing assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content

    except Exception as e:
        messagebox.showerror("OpenAI Error", f"OpenAI API call failed: {e}")
        return ""

def parse_response_for_csv_and_letter(full_text: str):
    """
    Splits the LLM's combined output into:
      - CSV portion (section,subsection,content lines)
      - Cover letter portion (beginning with "Dear ")
    """
    csv_marker = "section,subsection,content"
    letter_marker = "Dear "

    csv_part = ""
    letter_part = ""

    if csv_marker in full_text:
        start_idx = full_text.index(csv_marker)
        csv_part = full_text[start_idx:]
        if letter_marker in csv_part:
            letter_idx = csv_part.index(letter_marker)
            letter_part = csv_part[letter_idx:].strip()
            csv_part = csv_part[:letter_idx].strip()
        else:
            letter_part = "Could not parse letter. 'Dear ' not found in output."
    else:
        csv_part = "Could not parse CSV. 'section,subsection,content' not found."
        letter_part = full_text

    return csv_part, letter_part

def main():
    load_dotenv()
    # Use OPENAI_API_KEY or HUGGING_CHAT_API_KEY
    openai.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("HUGGING_CHAT_API_KEY")
    if not openai.api_key:
        tk.messagebox.showerror("Error", "No OpenAI API key found in environment.")
        sys.exit(1)

    # We'll assume your master CSV is named resume_data_master.csv
    csv_file = "resume_data_master.csv"
    if not os.path.isfile(csv_file):
        tk.messagebox.showerror("Error", f"{csv_file} not found in directory.")
        sys.exit(1)

    df_master = pd.read_csv(csv_file)
    if df_master.empty:
        tk.messagebox.showerror("Error", "The master CSV is empty.")
        sys.exit(1)

    # Show a dialog for the user to paste job description
    job_description = get_job_description_from_dialog()
    if not job_description:
        tk.messagebox.showinfo("Info", "No job description entered. Exiting.")
        sys.exit(0)

    # Turn entire master CSV into text
    master_csv_text = df_master.to_csv(index=False)

    # 1) Call the LLM
    raw_output = call_llm_to_shorten_resume(job_description, master_csv_text)

    # 2) Parse out CSV & letter
    short_csv, cover_letter = parse_response_for_csv_and_letter(raw_output)

    # 3) Save them
    tailored_csv_path = "tailored_resume.csv"
    cover_letter_path = "cover_letter.txt"
    pdf_path = "tailored_resume.pdf"

    with open(tailored_csv_path, "w", encoding="utf-8") as f:
        f.write(short_csv)

    with open(cover_letter_path, "w", encoding="utf-8") as f:
        f.write(cover_letter)

    # 4) Call resume.py to make PDF
    try:
        subprocess.run(["python", "resume.py", tailored_csv_path, pdf_path], check=True)
        msg = (
            f"Successfully generated:\n\n"
            f" - {pdf_path}\n"
            f" - {cover_letter_path}\n\n"
            f"Raw LLM output:\n\n"
            f"{raw_output}"
        )
        tk.messagebox.showinfo("Success", msg)

    except subprocess.CalledProcessError as e:
        tk.messagebox.showerror("Error Generating PDF", f"resume.py failed: {e}")

if __name__ == "__main__":
    main()
