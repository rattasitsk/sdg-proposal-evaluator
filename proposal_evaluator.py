import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv
import pypdf
import docx
import pandas as pd  # Import pandas for creating the data frame
import re

# Constants
load_dotenv()
CHATGEN_API_KEY = os.getenv("CHATGEN_API_KEY")
API_URL = "https://chatgen.scmc.cmu.ac.th/api/chat/completions"

# --- File Reading Functions ---
@st.cache_data  # Cache the results for faster access
def read_pdf(file):
    try:
        pdf_reader = pypdf.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

@st.cache_data  # Cache the results for faster access
def read_docx(file):
    try:
        doc = docx.Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {e}")
        return None

def evaluate_proposal(proposal_text, language="thai"):
    """
    Evaluates a proposal against SDG targets using ChatGenAI.
    Expects plain-text output.
    """
    prompt = f"""
    You are an expert in evaluating project proposals against the United Nations Sustainable Development Goals (SDGs).
    Your task is to analyze the provided project proposal text and assign a score from 0 to 10 for each of the 17 SDGs.
    Also provide a short justification for the score in Thai language.

    Here is the project proposal text:
    {proposal_text}

    Provide your analysis in the following format:
    SDG 1: [Score] - [Explanation]
    SDG 2: [Score] - [Explanation]
    ...
    SDG 17: [Score] - [Explanation]

    Ensure your response follows the specified format strictly.
    """

    headers = {
        "Authorization": f"Bearer {CHATGEN_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        response_json = response.json()
        evaluation_content = response_json["choices"][0]["message"]["content"]

        if not evaluation_content:  # Check if content is empty
            st.error("API returned empty content.")
            return None

        return evaluation_content #Return it without stripping or decoding JSON

    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return None

def parse_evaluation_text(evaluation_text):
    """Parses the plain-text evaluation and returns a dictionary."""
    results = {}
    lines = evaluation_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("SDG"):
            try:
                parts = line.split(":", 1)
                sdg = parts[0].strip()
                # Extract SDG Number and make it the key
                sdg_number = int(re.search(r'(\d+)', sdg).group(1))
                score_and_explanation = parts[1].strip()
                score, explanation = score_and_explanation.split(" - ", 1)
                results[sdg_number] = {"score": score.strip(), "explanation": explanation.strip()} # Change SDG to an Integer
            except ValueError:
                print(f"Could not parse line: {line}")
    return results

def main():
    st.title("SDG Proposal Evaluator (Thai)")

    uploaded_file = st.file_uploader("Upload Proposal (PDF or DOCX)", type=["pdf", "docx"])

    if uploaded_file is not None:
        file_type = uploaded_file.type
        file_name = uploaded_file.name

        # Read the file content based on its type
        if file_type == "application/pdf":
            proposal_text = read_pdf(uploaded_file)
        elif file_type =="application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            proposal_text = read_docx(uploaded_file)
        else:
            st.error(f"Error reading PDF or DOCX: {e}")
            proposal_text = None

        if proposal_text:
            st.subheader("Proposal Text Preview:")
            st.text(proposal_text[:500] + "..." if len(proposal_text) > 500 else proposal_text)

        if st.button("Evaluate Proposal"):
            with st.spinner("Evaluating with ChatGenAI..."):
                # --- Progress Bar ---
                progress_bar = st.progress(0) # Initial progress
                progress_text = st.empty() # For updating status text

                try:
                    progress_text.text("Step 1: Preparing evaluation...")

                    progress_bar.progress(25)
                    progress_text.text("Step 2: Sending data to ChatGenAI...")
                    evaluation_result = evaluate_proposal(proposal_text, language="Thai")

                    progress_bar.progress(75)
                    progress_text.text("Step 3: Processing results...")

                    progress_bar.progress(100)
                    progress_text.text("Evaluation complete!")

                except Exception as e:
                    st.error(f"An error occurred during evaluation: {e}")
                    progress_text.text("Evaluation failed.")
                    progress_bar.empty() # Hide the progress bar
                if evaluation_result:
                    # --- Parse the plain-text output ---
                    parsed_results = parse_evaluation_text(evaluation_result) #Remove overall_score here

                    st.subheader("Evaluation Results:")

                    # --- Bar Chart ---
                    sdg_data = {
                        "SDG": list(parsed_results.keys()),
                        "Score": [int(data['score']) for data in parsed_results.values()]
                    }
                    sdg_df = pd.DataFrame(sdg_data)
                    sdg_df = sdg_df.sort_values('SDG')
                    st.bar_chart(data=sdg_df, x="SDG", y="Score")

                    for sdg, data in parsed_results.items():
                        st.write(f"**SDG {sdg}:** {data['score']} - {data['explanation']}")
if __name__ == "__main__":
    main()