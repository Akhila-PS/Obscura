import os
import json
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Try to load either from current backend dir or parent
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if not os.path.exists(env_path):
    # Try one level up if in different execution context
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    
load_dotenv(env_path)

def get_llm_client():
    """
    Initialize the Gemini client.
    Expects GEMINI_API_KEY to be set in the environment.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key and api_key.startswith('"') and api_key.endswith('"'):
        api_key = api_key[1:-1]
        
    if not api_key:
        print("⚠️ WARNING: GEMINI_API_KEY environment variable not set. LLM features will be disabled.")
        return None
    
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"❌ ERROR initializing Gemini client: {e}")
        return None

def generate_redaction_summary(ocr_results, detection_results, custom_prompt=None):
    """
    Generates a natural language summary of what was found and redacted.
    """
    client = get_llm_client()
    if not client:
        return "AI Summarization is currently unavailable (Missing API Key)."
    
    # 1. Reconstruct the document text
    full_text = " ".join([text for _, text, _ in ocr_results])
    
    # 2. Reconstruct what we did
    actions = []
    for boxes, label, method in detection_results:
        actions.append(f"- {len(boxes)} instance(s) of '{label}' were {method}ed.")
    
    actions_str = "\n".join(actions) if actions else "No sensitive standard entities were found."
    
    custom_rule_context = ""
    if custom_prompt:
        custom_rule_context = f"\nAdditionally, the user provided this custom rule for redaction: '{custom_prompt}'. Please mention if this rule resulted in any redactions assuming 'Custom Rule Match' actions correspond to it."
    
    prompt = f"""
    You are a privacy compliance assistant for a document redaction platform called Obscura.
    The user uploaded a document. We ran OCR and automated redaction on the document.
    
    Here is the full OCR text extracted from the document:
    '''
    {full_text}
    '''
    
    Here is the list of redaction actions our system took based on built-in rules and user settings:
    {actions_str}
    {custom_rule_context}
    
    Your task is to write a brief, professional summary (3-5 sentences) intended for the user. 
    1. Briefly summarize what kind of document this appears to be (e.g., an invoice, a medical record, an ID card).
    2. Summarize what exact types of sensitive data were protected/redacted. Do NOT reveal the actual sensitive data itself in the summary, just the types (like 'a phone number' or 'the patient name').
    3. Make it clear and reassuring.
    """
    
    try:
        print("🤖 Generating AI Redaction Summary... (Calling Gemini API)")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        print("🤖 AI Redaction Summary: Received response from Gemini API!")
        return response.text.strip()
    except Exception as e:
        print(f"❌ ERROR generating summary: {e}")
        traceback.print_exc()
        return "An error occurred while generating the AI summary."


def detect_custom_rules(ocr_results, custom_prompt):
    """
    Uses the LLM to find text matching the custom_prompt and returns bounding boxes.
    """
    if not custom_prompt or not custom_prompt.strip():
        return []
        
    client = get_llm_client()
    if not client:
        print("⚠️ Cannot run Smart Redaction without Gemini API Key.")
        return []
        
    # We need to give the LLM the text AND an ID for each bounding box so it can tell us which boxes to redact.
    indexed_text = []
    for i, (bbox, text, conf) in enumerate(ocr_results):
        indexed_text.append(f"[{i}] {text}")
        
    document_content = "\n".join(indexed_text)
    
    prompt = f"""
    You are an intelligent data redaction assistant.
    The user has provided a custom redaction rule: "{custom_prompt}"
    
    Below is the text extracted from a document via OCR. Each line has an index number in brackets, followed by the text.
    
    Your task is to identify which indices contain text that should be redacted according to the user's rule.
    
    OCR Text:
    '''
    {document_content}
    '''
    
    Analyze the text and the rule. Return ONLY a valid JSON array of the integer indices that should be redacted. 
    Do not return any markdown formatting, backticks, or other text. Just the JSON array.
    If nothing matches the rule, return an empty array: []
    Example output format: [3, 4, 12]
    """
    
    try:
        print(f"🧠 Running Smart Redaction for rule: '{custom_prompt}'... (Calling Gemini API)")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        print("🧠 Smart Redaction: Received response from Gemini API!")
        
        result_text = response.text.strip()
        
        # Clean up potential markdown formatting if the model disobeys instructions
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        result_text = result_text.strip()
        
        indices = json.loads(result_text)
        
        if not isinstance(indices, list):
            print(f"⚠️ Smart Redaction returned invalid format: {indices}")
            return []
            
        # Map indices back to boxes
        redact_boxes = []
        for idx in indices:
            if isinstance(idx, int) and 0 <= idx < len(ocr_results):
                redact_boxes.append(ocr_results[idx][0])
                print(f"   ✅ Smart Match found: '{ocr_results[idx][1]}'")
                
        return redact_boxes
        
    except json.JSONDecodeError:
        print(f"❌ ERROR parsing Smart Redaction JSON response: {response.text}")
        return []
    except Exception as e:
        print(f"❌ ERROR in Smart Redaction: {e}")
        traceback.print_exc()
        return []


def detect_sensitive_entities_ai(ocr_results, active_redactions, custom_prompt=""):
    """
    Unified function to find various sensitive entities using Gemini.
    """
    if not active_redactions and not custom_prompt.strip():
        return {}
        
    client = get_llm_client()
    if not client:
        print("⚠️ Cannot run Smart AI Redaction without Gemini API Key.")
        return {}
        
    indexed_text = []
    for i, (bbox, text, conf) in enumerate(ocr_results):
        indexed_text.append(f"[{i}] {text}")
        
    document_content = "\n".join(indexed_text)
    
    redaction_goals = []
    for r in active_redactions:
        if r == "general_pii":
            redaction_goals.append("- general_pii: General Personally Identifiable Information (Driver's License IDs, Passport Numbers, Dates of Birth, Expiry Dates, Social Security Numbers, etc.)")
        else:
            redaction_goals.append(f"- {r}")
            
    goals_str = "\n".join(redaction_goals)
    
    custom_instruction = ""
    if custom_prompt.strip():
        custom_instruction = f"\nAdditionally, follow this custom user rule: '{custom_prompt}'"
    
    prompt = f"""
    You are an intelligent data redaction assistant.
    
    Below is the text extracted from a document via OCR. Each line has an index number in brackets, followed by the text.
    
    Your task is to identify which indices contain text that should be redacted based on the requested entity types.
    
    Requested Entity Types to Redact:
    {goals_str}
    {custom_instruction}
    
    OCR Text:
    '''
    {document_content}
    '''
    
    Analyze the text. Return ONLY a valid JSON object where keys are the identified entity types (e.g., 'aadhaar', 'phone', 'email', 'custom') 
    and values are arrays of the integer indices that should be redacted for that type.
    
    Do not return any markdown formatting, backticks, or other text. Just the JSON object.
    If nothing matches, return an empty object: {{}}
    Example output format: {{"aadhaar": [3, 4], "phone": [12], "custom": [15, 16]}}
    """
    
    try:
        print(f"🧠 Running Unified AI Redaction for {len(active_redactions)} standard types and custom rules... (Calling Gemini)")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        print("🧠 Unified AI Redaction: Received response from Gemini API!")
        
        result_text = response.text.strip()
        
        # Clean up potential markdown formatting
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        result_text = result_text.strip()
        
        categorized_indices = json.loads(result_text)
        
        if not isinstance(categorized_indices, dict):
            print(f"⚠️ Unified AI Redaction returned invalid format: {categorized_indices}")
            return {}
            
        # Map indices back to boxes
        categorized_boxes = {}
        for category, indices in categorized_indices.items():
            boxes_for_category = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(ocr_results):
                    boxes_for_category.append(ocr_results[idx][0])
                    print(f"   ✅ AI found '{category}' match: '{ocr_results[idx][1]}'")
            
            if boxes_for_category:
                categorized_boxes[category] = boxes_for_category
                
        return categorized_boxes
        
    except json.JSONDecodeError:
        print(f"❌ ERROR parsing Unified AI Redaction JSON response: {response.text}")
        return {}
    except Exception as e:
        print(f"❌ ERROR in Unified AI Redaction: {e}")
        traceback.print_exc()
        return {}
