import pandas as pd
import time
import os
from app import generate_with_gemini

def read_excel(file_path):
    """Read sentences from the first column of an Excel file"""
    try:
        df = pd.read_excel(file_path)
        if df.empty:
            return None, "The uploaded Excel file is empty."
        
        column_name = df.columns[0]
        sentences = df[column_name].tolist()
        return sentences, None
    except Exception as e:
        return None, f"Error reading Excel file: {str(e)}"

def process_sentences(sentences):
    """Process each sentence, building up the story and generating prompts"""
    results = []
    story_so_far = ""
    
    for i, sentence in enumerate(sentences):
        if i > 0:
            # Add a 4-second delay after the first API call
            time.sleep(4)
        
        # Update the story with the current sentence
        if i == 0:
            story_so_far = sentence
        else:
            story_so_far += " " + sentence

       
        
        # Generate prompt for the current sentence using the format from the user's requirements
        prompt = f"[Full_story]\n{story_so_far}\n[Sentence i] {sentence}\n\nGenerate a detailed prompt of this sentence related to the full story. Write only one prompt, no text in image ."
        
        # Call Gemini API through app.py's function
        generated_prompt = generate_with_gemini(prompt)
        
        # Store the result
        results.append({
            "Original Sentence": sentence,
            "Generated Prompt": generated_prompt
        })
        
        print(f"Processed sentence {i+1}/{len(sentences)}")
    
    return results

def save_results(results, output_file):
    """Save results to a new Excel file"""
    df = pd.DataFrame(results)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    df.to_excel(output_file, index=False)
    return output_file

def main(input_file, output_file="results.xlsx"):
    """Main function to orchestrate the prompt generation process"""
    print(f"Processing Excel file: {input_file}")
    print(f"Output will be saved to: {output_file}")
    
    # Read sentences from Excel
    sentences, error = read_excel(input_file)
    if error:
        print(f"Error: {error}")
        return None, error
    
    print(f"Found {len(sentences)} sentences to process")
    
    # Process sentences
    results = process_sentences(sentences)
    
    # Save results
    output_path = save_results(results, output_file)
    print(f"Results saved to: {output_path}")
    
    return output_path, None

if __name__ == "__main__":
    # For testing from command line
    import sys
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "results.xlsx"
        output_path, error = main(input_file, output_file)
        
        if error:
            print(f"Error: {error}")
        else:
            print(f"Results saved to: {output_path}")
    else:
        print("Please provide the path to an Excel file.")
        print("Usage: python main.py input_file.xlsx [output_file.xlsx]") 