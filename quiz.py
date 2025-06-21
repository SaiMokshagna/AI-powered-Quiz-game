import tkinter as tk
from tkinter import messagebox
import requests
import random
import uuid
import concurrent.futures
from PIL import Image, ImageTk, ImageDraw
import math
import time
import os

# --- Constants ---
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
API_KEY = "aAIzaSyAa20OkB7cfPWUMH3tVNoyETZjidpYyN2E"  # User's Gemini API key
USE_API_QUESTIONS = True  # Set to False to use only placeholder questions for faster loading

# --- Asset Path Helper ---
# Get the absolute path of the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_asset_path(filename):
    """Constructs the absolute path for an asset file."""
    return os.path.join(SCRIPT_DIR, filename)

# --- Data Structures ---
class Question:
    def __init__(self, question, options, correct_answer, category, difficulty, explanation):
        self.id = str(uuid.uuid4())
        self.question = question
        self.options = options
        self.correct_answer = correct_answer
        self.category = category
        self.difficulty = difficulty
        self.explanation = explanation

# --- Main App ---
class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Quiz Game")
        self.root.geometry("900x600")  # Set a default window size
        self.difficulty = tk.StringVar(value="Easy")
        self.current_screen = None
        self.questions = []
        self.current_question_index = 0
        self.score = 0
        self.selected_option = tk.StringVar()
        self.is_loading = False
        self.user_answers = []  # Store (selected_option) for each question
        self.error_message = None
        self.build_opening_screen()

    def build_opening_screen(self):
        self.clear_screen()
        self.opening_frame = tk.Frame(self.root)
        self.opening_frame.pack(fill="both", expand=True)

        self.start_btn_width = 200
        self.start_btn_height = 50

        try:
            self.opening_img_orig = Image.open(get_asset_path("open1.jpeg"))
        except Exception as e:
            print("Image load error:", e)
            self.opening_img_orig = None

        self.bg_label = tk.Label(self.opening_frame)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Standard rectangular Start Quiz button
        self.start_btn = tk.Button(
            self.opening_frame, text="Start Quiz", command=self._start_quiz_from_opening,
            font=("Arial", 18, "bold"), bg="#14b8a6", fg="#ffffff",
            activebackground="#0d9488", activeforeground="#ffffff",
            borderwidth=0, relief="flat", cursor="hand2"
        )
        self.start_btn.place(x=0, y=0, width=self.start_btn_width, height=self.start_btn_height)

        self.root.bind("<Configure>", self.on_opening_resize)
        self.on_opening_resize()  # Initial placement

        self.current_screen = self.opening_frame

    def _start_quiz_from_opening(self):
        # Unbind the resize event when leaving the opening screen
        self.root.unbind("<Configure>")
        self.build_start_screen()

    def on_opening_resize(self, event=None):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        if w < 300 or h < 200:
            w, h = 900, 600

        if hasattr(self, 'opening_img_orig') and self.opening_img_orig:
            img = self.opening_img_orig.resize((w, h), Image.LANCZOS)
            self.opening_img = ImageTk.PhotoImage(img)
            self.bg_label.config(image=self.opening_img)
            self.bg_label.image = self.opening_img

        btn_x = (w - self.start_btn_width) // 2
        btn_y = int(h * 0.85) - self.start_btn_height // 2
        self.start_btn.place(x=btn_x, y=btn_y, width=self.start_btn_width, height=self.start_btn_height)

    def build_start_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        self.bg_img_path = get_asset_path("image2.jpeg")
        self.diff_bg_img_orig = None
        try:
            self.diff_bg_img_orig = Image.open(self.bg_img_path)
        except Exception as e:
            print("Image load error:", e)
            self.diff_bg_img_orig = None

        self.diff_canvas = tk.Canvas(frame, highlightthickness=0)
        self.diff_canvas.pack(fill="both", expand=True)
        self.diff_btn_areas = []
        self.diff_btn_labels = ["Easy", "Medium", "Hard"]
        self.diff_btn_colors = [(0, 191, 255, 255), (0, 191, 255, 255), (0, 191, 255, 255)]  # Electric blue, fully opaque

        def on_canvas_click(event):
            for btn in self.diff_btn_areas:
                if btn["x1"] <= event.x <= btn["x2"] and btn["y1"] <= event.y <= btn["y2"]:
                    self.difficulty.set(btn["level"])
                    self.start_quiz()
                    break
        self.diff_canvas.bind("<Button-1>", on_canvas_click)

        def on_resize(event=None):
            if event is not None:
                w = event.width
                h = event.height
            else:
                w = self.diff_canvas.winfo_width()
                h = self.diff_canvas.winfo_height()
            if w < 100 or h < 100 or not self.diff_bg_img_orig:
                return
            # Draw background image
            img = self.diff_bg_img_orig.resize((w, h), Image.LANCZOS)
            self.diff_bg_img = ImageTk.PhotoImage(img)
            self.diff_canvas.delete("all")
            self.diff_canvas.create_image(0, 0, anchor="nw", image=self.diff_bg_img)
            # Draw translucent buttons
            btn_w = int(w * 0.15)  # Slightly smaller width for vertical layout
            btn_h = int(h * 0.12)  # Slightly smaller height for vertical layout
            btn_x = int(w * 0.05)  # Position on left side with small margin
            spacing = int((h - 3 * btn_h) / 4)  # Vertical spacing between buttons
            self.diff_btn_areas.clear()
            if not hasattr(self, 'btn_imgs_refs'):
                self.btn_imgs_refs = []
            self.btn_imgs_refs.clear()
            for i, label in enumerate(self.diff_btn_labels):
                x1 = btn_x
                y1 = spacing + i * (btn_h + spacing)
                x2 = x1 + btn_w
                y2 = y1 + btn_h
                # Draw translucent rectangle using PIL
                pil_btn = Image.new("RGBA", (btn_w, btn_h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(pil_btn)
                # Calculate radius for rounded corners (about 10% of button height)
                radius = int(btn_h * 0.1)
                draw.rounded_rectangle((0, 0, btn_w, btn_h), radius=radius, fill=self.diff_btn_colors[i], outline=None)
                btn_img = ImageTk.PhotoImage(pil_btn)
                self.diff_canvas.create_image(x1, y1, anchor="nw", image=btn_img)
                self.btn_imgs_refs.append(btn_img)
                # Draw label
                self.diff_canvas.create_text((x1 + x2)//2, (y1 + y2)//2, text=label, font=("Arial", int(btn_h*0.35), "bold"), fill="#fff")
                # Store clickable area
                self.diff_btn_areas.append({
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2, "level": label
                })
        self.diff_canvas.bind("<Configure>", on_resize)
        on_resize()  # Initial draw
        self.current_screen = frame

    def start_quiz(self):
        self.clear_screen()
        self.session_id = str(uuid.uuid4())  # Generate a unique session ID for this quiz
        self.show_loading_screen()
        self.root.after(100, self.fetch_questions_from_gemini)

    def show_loading_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        self.loading_bg_img_orig = None
        try:
            self.loading_bg_img_orig = Image.open(get_asset_path("load.jpg"))
        except Exception as e:
            print("Image load error:", e)

        self.loading_canvas = tk.Canvas(frame, highlightthickness=0)
        self.loading_canvas.pack(fill="both", expand=True)

        self.loading_label = tk.Label(
            self.loading_canvas, text="Loading questions...",
            font=("Arial", 22, "bold"), bg="#18181b", fg="white"
        )

        def on_resize(event=None):
            if not self.loading_bg_img_orig: return
            w = self.loading_canvas.winfo_width()
            h = self.loading_canvas.winfo_height()
            if w < 100: w = 900
            if h < 100: h = 600

            # Draw background
            img = self.loading_bg_img_orig.resize((w, h), Image.LANCZOS)
            self.loading_bg_img = ImageTk.PhotoImage(img)
            self.loading_canvas.delete("all")
            self.loading_canvas.create_image(0, 0, anchor="nw", image=self.loading_bg_img)
            
            # Create and draw the translucent panel for the text
            panel_w, panel_h = 350, 80
            panel_x, panel_y = (w - panel_w) // 2, (h - panel_h) // 2

            panel_img = Image.new("RGBA", (panel_w, panel_h))
            draw = ImageDraw.Draw(panel_img)
            draw.rounded_rectangle((0, 0, panel_w, panel_h), radius=15, fill=(24, 24, 27, 190))
            
            self.loading_panel_photo = ImageTk.PhotoImage(panel_img)
            self.loading_canvas.create_image(panel_x, panel_y, image=self.loading_panel_photo, anchor="nw")

            # Place the label on top of the panel
            self.loading_canvas.create_window(w/2, h/2, window=self.loading_label, anchor="center")

        self.loading_canvas.bind("<Configure>", on_resize)
        on_resize()

        self.current_screen = frame

    def fetch_questions_from_gemini(self):
        try:
            difficulty = self.difficulty.get()
            session_id = getattr(self, 'session_id', str(uuid.uuid4()))
            
            # Check if we should use API questions or placeholders
            if not USE_API_QUESTIONS:
                print("DEBUG: Using placeholder questions only for faster loading.")
                self.questions = self.get_placeholder_questions()[:15]  # Get 15 questions
                self.current_question_index = 0
                self.score = 0
                self.user_answers = [None] * len(self.questions)
                self.error_message = None
                self.is_loading = False
                self.root.after(100, self.show_quiz_screen)
                return
            
            prompts = []
            
            # --- Define categories and question counts ---
            categories = {
                "Current Affairs": 3,  # Reduced from 4 to 3
                "Sports": 3,           # Reduced from 4 to 3
                "General Knowledge": 3, # Reduced from 4 to 3
                "History": 3,          # Reduced from 4 to 3
                "Mental Ability": 3    # Reduced from 4 to 3
            }
            total_questions_needed = sum(categories.values())

            # --- Create initial prompts ---
            def create_prompt(category, seed):
                if category == "Current Affairs":
                    return f"Session ID: {session_id}. Seed: {seed}. Generate a UNIQUE {difficulty} multiple-choice question about a real, recent (within the last 3 months) current affairs event in India. Do not repeat questions from previous sessions. Provide 4 plausible options, only one of which is correct. Include the correct answer and a detailed explanation. Output the result as a JSON object with keys: question, options, correctAnswer, explanation."
                elif category == "Sports":
                    return f"Session ID: {session_id}. Seed: {seed}. Generate a UNIQUE {difficulty} multiple-choice question about sports. Do not repeat questions from previous sessions. Provide 4 plausible options, only one of which is correct. Include the correct answer and a detailed explanation. Output the result as a JSON object with keys: question, options, correctAnswer, explanation."
                elif category == "General Knowledge":
                    return f"Session ID: {session_id}. Seed: {seed}. Generate a UNIQUE {difficulty} multiple-choice General Knowledge question. Do not repeat questions from previous sessions. Provide 4 plausible options, only one of which is correct. Include the correct answer and a brief explanation. Output the result as a JSON object with keys: question, options, correctAnswer, explanation."
                elif category == "History":
                    return f"Session ID: {session_id}. Seed: {seed}. Generate a UNIQUE {difficulty} multiple-choice question about world or Indian history. Do not repeat questions from previous sessions. Provide 4 plausible options, only one of which is correct. Include the correct answer and a brief explanation. Output the result as a JSON object with keys: question, options, correctAnswer, explanation."
                elif category == "Mental Ability":
                    return f"Session ID: {session_id}. Seed: {seed}. Generate a UNIQUE {difficulty} multiple-choice mental ability or logical reasoning question. Examples: number series, coding-decoding, analogies. Do not repeat questions from previous sessions. Provide 4 plausible options, only one of which is correct. Include the correct answer and a brief explanation. Output the result as a JSON object with keys: question, options, correctAnswer, explanation."
                return None

            for category, num in categories.items():
                for _ in range(num):
                    random_seed = str(uuid.uuid4())
                    prompt_text = create_prompt(category, random_seed)
                    if prompt_text:
                        prompts.append((prompt_text, category))

            random.shuffle(prompts)

            max_retries = 1  # Reduced from 2 to 1 for faster fallback
            all_questions = []
            seen_questions = set()
            rate_limit_count = 0  # Track rate limit errors

            def chunks(lst, n):
                """Yield successive n-sized chunks from lst."""
                for i in range(0, len(lst), n):
                    yield lst[i:i + n]

            for attempt in range(max_retries + 1):
                
                prompt_chunks = list(chunks(prompts, 5)) # Increased batch size back to 5 for faster processing

                for i, chunk in enumerate(prompt_chunks):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:  # Increased workers to 3
                        # Fetch questions in the current batch concurrently
                        results = list(executor.map(
                            lambda p_args: self.get_question_from_gemini_with_retries(p_args[0], p_args[1], difficulty),
                            chunk
                        ))
                    
                    # Count rate limit errors
                    failed_requests = sum(1 for r in results if r is None)
                    if failed_requests > 0:
                        rate_limit_count += failed_requests
                    
                    # Add new unique questions from this batch's results
                    for q in results:
                        if q and q.question not in seen_questions:
                            all_questions.append(q)
                            seen_questions.add(q.question)

                    # Reduced pause between batches for faster processing
                    if i < len(prompt_chunks) - 1:
                        time.sleep(3)  # Reduced from 8 to 3 seconds

                # If we got too many rate limit errors, switch to placeholders immediately
                if rate_limit_count >= 3:  # Reduced from 5 to 3 for faster fallback
                    print("DEBUG: Too many rate limit errors, switching to placeholder questions.")
                    break

                if len(all_questions) >= total_questions_needed:
                    break  # We have enough questions

                # If not enough, prepare new prompts for the next retry
                if attempt < max_retries:
                    # Reduced delay between retry attempts
                    time.sleep(8)  # Reduced from 15 to 8 seconds
                    needed = total_questions_needed - len(all_questions)
                    prompts = []  # Create new prompts for the remaining needed questions
                    
                    # Create a flat list of categories to randomly choose from
                    category_pool = []
                    for cat, num in categories.items():
                        # Get count of questions we already have for this category
                        current_count = sum(1 for q in all_questions if q.category == cat)
                        # Add the category to the pool for the number of times it's still needed
                        category_pool.extend([cat] * (num - current_count))
                    
                    for _ in range(needed):
                        if not category_pool: break
                        cat = random.choice(category_pool)
                        category_pool.remove(cat) # Avoid over-picking
                        
                        random_seed = str(uuid.uuid4())
                        prompt = create_prompt(cat, random_seed)
                        if prompt:
                            prompts.append((prompt, cat))
            
            # If still not enough, fill with placeholders
            if len(all_questions) < total_questions_needed:
                print("DEBUG: Not enough unique questions from Gemini after retries, using placeholder questions.")
                needed = total_questions_needed - len(all_questions)
                placeholders = self.get_placeholder_questions()
                # Only add placeholders that are not duplicates
                for q in placeholders:
                    if len(all_questions) >= total_questions_needed:
                        break
                    if q.question not in [qq.question for qq in all_questions]:
                        # Make sure placeholder category matches a needed category
                        current_counts = {cat: sum(1 for q_existing in all_questions if q_existing.category == cat) for cat in categories}
                        if current_counts.get(q.category, 0) < categories.get(q.category, 0):
                            all_questions.append(q)

            self.questions = all_questions[:total_questions_needed]
            self.current_question_index = 0
            self.score = 0
            self.user_answers = [None] * len(self.questions)
            self.error_message = None
            self.is_loading = False
            self.root.after(100, self.show_quiz_screen)
        except Exception as e:
            self.error_message = f"Error loading questions: {e}"
            self.is_loading = False
            self.root.after(100, self.show_error_screen)

    def get_question_from_gemini_with_retries(self, prompt, category, difficulty, max_retries=3):
        for attempt in range(max_retries):
            q = self.get_question_from_gemini(prompt, category, difficulty)
            if q:
                return q
            # Reduced exponential backoff: wait shorter between retries
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 2  # Reduced from 5 to 2: 2, 4, 8 seconds
                print(f"DEBUG: Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        return None

    def get_question_from_gemini(self, prompt, category, difficulty):
        try:
            url = f"{API_URL}?key={API_KEY}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            
            # Handle rate limit errors specifically
            if resp.status_code == 429:
                print("DEBUG: Rate limit hit, will retry with backoff")
                return None
                
            resp.raise_for_status()
            result = resp.json()
            # Parse the JSON from the AI's response
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            print("DEBUG: Gemini raw response:", text)  # Debug output
            import json as pyjson
            try:
                qdata = pyjson.loads(text)
            except Exception as e:
                print("DEBUG: JSON decode error:", e)
                return None
            if not qdata:
                return None
            question = qdata.get("question")
            options = qdata.get("options")
            correct_answer = qdata.get("correctAnswer")
            explanation = qdata.get("explanation", "")
            if not (question and options and correct_answer):
                return None
            return Question(question, options, correct_answer, category, difficulty, explanation)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print("DEBUG: Rate limit error, will retry")
                return None
            else:
                print("DEBUG: HTTP error in get_question_from_gemini:", e)
                return None
        except Exception as e:
            print("DEBUG: Exception in get_question_from_gemini:", e)
            return None

    def get_placeholder_questions(self):
        # 4 each for: Current Affairs, Sports, GK, History, Mental Ability
        return [
            # India Current Affairs (4)
            Question("Who is the current President of India as of 2024?",["Draupadi Murmu", "Ram Nath Kovind", "Pranab Mukherjee", "Narendra Modi"],"Draupadi Murmu","Current Affairs","Easy","Draupadi Murmu became the President of India in July 2022."),
            Question("Which Indian city hosted the G20 Summit in 2023?",["New Delhi", "Mumbai", "Bengaluru", "Hyderabad"],"New Delhi","Current Affairs","Medium","The G20 Summit 2023 was held in New Delhi, India."),
            Question("Which Indian state was affected by Cyclone Biparjoy in June 2023?",["Gujarat", "West Bengal", "Odisha", "Kerala"],"Gujarat","Current Affairs","Medium","Cyclone Biparjoy made landfall in Gujarat in June 2023."),
            Question("Who is the current Chief Minister of Tamil Nadu as of 2024?",["M.K. Stalin", "Edappadi K. Palaniswami", "Pinarayi Vijayan", "Yogi Adityanath"],"M.K. Stalin","Current Affairs","Easy","M.K. Stalin is the Chief Minister of Tamil Nadu since 2021."),
            
            # Sports (4)
            Question("Who won the 2023 Cricket World Cup?",["Australia", "India", "England", "New Zealand"],"Australia","Sports","Medium","Australia won the 2023 ICC Cricket World Cup."),
            Question("Which Indian athlete won a gold medal in javelin at the Tokyo 2020 Olympics?",["Neeraj Chopra", "Bajrang Punia", "P.V. Sindhu", "Dutee Chand"],"Neeraj Chopra","Sports","Easy","Neeraj Chopra won gold in javelin at the Tokyo 2020 Olympics."),
            Question("Which city hosted the 2022 Commonwealth Games?",["Birmingham", "Gold Coast", "Delhi", "Glasgow"],"Birmingham","Sports","Medium","The 2022 Commonwealth Games were held in Birmingham, UK."),
            Question("How many players are on a standard soccer team on the field at one time?", ["11", "9", "7", "12"], "11", "Sports", "Easy", "A standard soccer team has 11 players on the field."),

            # General Knowledge (4)
            Question("What is the capital of India?",["New Delhi", "Mumbai", "Kolkata", "Chennai"],"New Delhi","General Knowledge","Easy","New Delhi is the capital city of India."),
            Question("Who wrote the Indian national anthem?",["Rabindranath Tagore", "Bankim Chandra Chatterjee", "Sarojini Naidu", "Subhas Chandra Bose"],"Rabindranath Tagore","General Knowledge","Easy","Rabindranath Tagore wrote the Indian national anthem, 'Jana Gana Mana'."),
            Question("Which river is known as the 'Ganga of the South'?",["Godavari", "Krishna", "Cauvery", "Yamuna"],"Godavari","General Knowledge","Medium","The Godavari river is often called the 'Ganga of the South'."),
            Question("What is the largest mammal in the world?", ["Blue Whale", "Elephant", "Giraffe", "Great White Shark"], "Blue Whale", "General Knowledge", "Easy", "The Blue Whale is the largest animal on Earth, known to have ever existed."),

            # History (4)
            Question("Who was the first Emperor of the Maurya Dynasty in India?", ["Chandragupta Maurya", "Ashoka", "Bindusara", "Samudragupta"], "Chandragupta Maurya", "History", "Medium", "Chandragupta Maurya founded the Maurya Empire in 322 BCE."),
            Question("The Battle of Plassey was fought in which year?", ["1757", "1857", "1764", "1801"], "1757", "History", "Hard", "The Battle of Plassey was a decisive victory of the British East India Company over the Nawab of Bengal and his French allies on 23 June 1757."),
            Question("Who is known as the 'Father of the Indian Constitution'?", ["Dr. B.R. Ambedkar", "Mahatma Gandhi", "Jawaharlal Nehru", "Sardar Vallabhbhai Patel"], "Dr. B.R. Ambedkar", "History", "Easy", "Dr. B.R. Ambedkar was the chairman of the Drafting Committee of the Constituent Assembly and is regarded as the Father of the Indian Constitution."),
            Question("The ancient city of Harappa is located in which present-day country?", ["Pakistan", "India", "Afghanistan", "Iran"], "Pakistan", "History", "Medium", "The ruins of Harappa are located in Punjab, Pakistan."),

            # Mental Ability (4)
            Question("Look at this series: 2, 1, (1/2), (1/4), ... What number should come next?", ["(1/8)", "(1/16)", "(1/2)", "1"], "(1/8)", "Mental Ability", "Easy", "This is a simple division series; each number is one-half of the previous number."),
            Question("If 'CAT' is coded as 'DOG', how is 'PIG' coded?", ["QJH", "QJG", "RJH", "QIH"], "QJH", "Mental Ability", "Medium", "Each letter in the word is moved one step forward in the alphabet."),
            Question("Which word does not belong with the others?", ["Apple", "Orange", "Banana", "Carrot"], "Carrot", "Mental Ability", "Easy", "All the others are fruits, while a carrot is a vegetable."),
            Question("A is the father of B. But B is not A's son. What is the relation between A and B?", ["Father and Daughter", "Father and Nephew", "Uncle and Nephew", "Father and Niece"], "Father and Daughter", "Mental Ability", "Easy", "If B is not A's son, then B must be A's daughter.")
        ]

    def show_quiz_screen(self):
        self.clear_screen()
        if self.current_question_index >= len(self.questions):
            self.show_score_screen()
            return
        
        q = self.questions[self.current_question_index]

        self.quiz_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.quiz_canvas.pack(fill="both", expand=True)

        try:
            self.quiz_bg_img_orig = Image.open(get_asset_path("load.jpg"))
        except Exception as e:
            print(f"Quiz background image load error: {e}")
            self.quiz_bg_img_orig = None

        self.selected_option.set(None)
        
        QUIZ_PANEL_COLOR = "#161618"
        self.quiz_widgets_frame = tk.Frame(self.quiz_canvas, bg=QUIZ_PANEL_COLOR)

        tk.Label(
            self.quiz_widgets_frame, text=f"Question {self.current_question_index + 1}/{len(self.questions)}",
            font=("Arial", 14, "bold"), bg=QUIZ_PANEL_COLOR, fg="#00e5ff"
        ).pack(pady=(15, 10))

        self.q_text_label = tk.Label(
            self.quiz_widgets_frame, text=q.question, font=("Arial", 16, "bold"),
            wraplength=550, justify="center", bg=QUIZ_PANEL_COLOR, fg="white"
        )
        self.q_text_label.pack(pady=10, padx=25)

        self.radio_buttons = []
        
        # Pre-select the user's previous answer for this question
        previous_answer = self.user_answers[self.current_question_index]
        self.selected_option.set(previous_answer)

        for opt in q.options:
            radio = tk.Radiobutton(
                self.quiz_widgets_frame, text=opt, variable=self.selected_option, value=opt,
                font=("Arial", 13), wraplength=530, justify="left",
                bg=QUIZ_PANEL_COLOR, fg="#e0e0e0", selectcolor="#424242",
                activebackground=QUIZ_PANEL_COLOR, activeforeground="white",
                highlightthickness=0, borderwidth=0, indicatoron=0,
                pady=10, padx=20
            )
            radio.pack(fill="x", padx=20, pady=4)
            self.radio_buttons.append(radio)

        # --- Navigation Buttons ---
        button_frame = tk.Frame(self.quiz_widgets_frame, bg=QUIZ_PANEL_COLOR)
        button_frame.pack(fill="x", pady=20, padx=20)
        
        self.prev_btn = tk.Button(
            button_frame, text="< Previous", font=("Arial", 14, "bold"),
            command=lambda: self.navigate_question(-1), bg="#14b8a6", fg="white",
            activebackground="#0d9488", borderwidth=0, relief="flat", cursor="hand2",
            state="disabled"
        )
        self.prev_btn.pack(side="left")

        self.next_btn = tk.Button(
            button_frame, font=("Arial", 14, "bold"), bg="#14b8a6", fg="white",
            activebackground="#0d9488", borderwidth=0, relief="flat", cursor="hand2"
        )
        self.next_btn.pack(side="right")

        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        if self.current_question_index > 0:
            self.prev_btn.config(state="normal")
            
        is_last_question = self.current_question_index == len(self.questions) - 1
        if is_last_question:
            self.next_btn.config(text="Finish", command=self.finish_quiz)
        else:
            self.next_btn.config(text="Next >", command=lambda: self.navigate_question(1))

        self.quiz_canvas.bind("<Configure>", self.on_quiz_resize)
        self.current_screen = self.quiz_canvas

    def on_quiz_resize(self, event):
        w, h = event.width, event.height
        
        # Draw background image
        if self.quiz_bg_img_orig:
            img = self.quiz_bg_img_orig.resize((w, h), Image.LANCZOS)
            self.quiz_bg_img = ImageTk.PhotoImage(img)
            self.quiz_canvas.delete("all")
            self.quiz_canvas.create_image(0, 0, anchor="nw", image=self.quiz_bg_img)
        else:
            self.quiz_canvas.config(bg="black")

        # Create translucent panel for content
        panel_w, panel_h = int(w * 0.8), int(h * 0.8)
        if panel_w < 600: panel_w = 600
        if panel_h < 500: panel_h = 500
        panel_x, panel_y = (w - panel_w) // 2, (h - panel_h) // 2

        panel_img = Image.new("RGBA", (panel_w, panel_h), (22, 22, 24, 190)) # Darker, more translucent
        self.panel_photo = ImageTk.PhotoImage(panel_img)
        self.quiz_canvas.create_image(panel_x, panel_y, image=self.panel_photo, anchor="nw")

        # Place widget frame on top
        self.q_text_label.config(wraplength=panel_w * 0.85)
        for radio in self.radio_buttons:
            radio.config(wraplength=panel_w * 0.8)
        self.quiz_canvas.create_window(w / 2, h / 2, window=self.quiz_widgets_frame, anchor="center")

    def navigate_question(self, direction):
        # Save the current answer before moving
        self.user_answers[self.current_question_index] = self.selected_option.get()

        if hasattr(self, 'quiz_canvas'):
            self.quiz_canvas.unbind("<Configure>")

        self.current_question_index += direction
        self.show_quiz_screen()

    def finish_quiz(self):
        # Save the answer for the final question
        self.user_answers[self.current_question_index] = self.selected_option.get()

        # Calculate score
        self.score = 0
        for i, q in enumerate(self.questions):
            if self.user_answers[i] == q.correct_answer:
                self.score += 1
        
        if hasattr(self, 'quiz_canvas'):
            self.quiz_canvas.unbind("<Configure>")
            
        self.show_score_screen()

    def restart_quiz(self):
        if hasattr(self, 'score_canvas'):
            self.score_canvas.unbind("<Configure>")
        self.build_start_screen()

    def show_score_screen(self):
        self.clear_screen()
        
        self.score_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.score_canvas.pack(fill="both", expand=True)

        try:
            self.score_bg_img_orig = Image.open(get_asset_path("bg.jpeg"))
        except Exception as e:
            print(f"Score screen background image load error: {e}")
            self.score_bg_img_orig = None

        PANEL_BG_COLOR = "#18181b"  # A dark, neutral color for the panel
        CARD_BG_COLOR = "#27272a"   # Slightly lighter for the cards
        
        # This frame holds all the widgets. Its background will match the panel.
        self.score_widgets_frame = tk.Frame(self.score_canvas, bg=PANEL_BG_COLOR)

        tk.Label(self.score_widgets_frame, text="Quiz Complete!", font=("Arial", 22, "bold"), bg=PANEL_BG_COLOR, fg="white").pack(pady=(20, 10))
        tk.Label(self.score_widgets_frame, text=f"Your Score: {self.score} / {len(self.questions)}", font=("Arial", 18), bg=PANEL_BG_COLOR, fg="#14b8a6").pack(pady=10)
        tk.Label(self.score_widgets_frame, text="Review Your Answers", font=("Arial", 14, "underline"), bg=PANEL_BG_COLOR, fg="#cccccc").pack(pady=10)

        review_container = tk.Frame(self.score_widgets_frame, bg=PANEL_BG_COLOR)
        review_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        canvas = tk.Canvas(review_container, bg=PANEL_BG_COLOR, highlightthickness=0)
        scrollbar = tk.Scrollbar(review_container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=PANEL_BG_COLOR)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for idx, q in enumerate(self.questions):
            user_ans = self.user_answers[idx] if self.user_answers[idx] is not None else "Not Answered"
            correct = (user_ans == q.correct_answer)
            color = "#4caf50" if correct else "#f44336"
            
            q_frame = tk.Frame(scroll_frame, bg=CARD_BG_COLOR, bd=1, relief="raised")
            q_frame.pack(fill="x", pady=8, padx=5)

            tk.Label(q_frame, text=f"Q{idx+1}: {q.question}", font=("Arial", 12, "bold"), wraplength=500, justify="left", bg=CARD_BG_COLOR, fg="white").pack(anchor="w", padx=10, pady=(5,0))
            tk.Label(q_frame, text=f"Your answer: {user_ans}", font=("Arial", 11), fg=color, wraplength=500, justify="left", bg=CARD_BG_COLOR).pack(anchor="w", padx=10)
            tk.Label(q_frame, text=f"Correct answer: {q.correct_answer}", font=("Arial", 11), wraplength=500, justify="left", bg=CARD_BG_COLOR, fg="white").pack(anchor="w", padx=10)
            tk.Label(q_frame, text=f"Explanation: {q.explanation}", font=("Arial", 10, "italic"), wraplength=500, justify="left", bg=CARD_BG_COLOR, fg="#cccccc").pack(anchor="w", padx=10, pady=(0,5))

        tk.Button(self.score_widgets_frame, text="Play Again", font=("Arial", 14, "bold"), command=self.restart_quiz, bg="#14b8a6", fg="white", activebackground="#0d9488", borderwidth=0).pack(pady=20)
        
        self.score_canvas.bind("<Configure>", self.on_score_resize)
        self.current_screen = self.score_canvas

    def on_score_resize(self, event):
        w, h = event.width, event.height

        if self.score_bg_img_orig:
            img = self.score_bg_img_orig.resize((w, h), Image.LANCZOS)
            self.score_bg_img = ImageTk.PhotoImage(img)
            self.score_canvas.delete("all")
            self.score_canvas.create_image(0, 0, anchor="nw", image=self.score_bg_img)
        else:
            self.score_canvas.config(bg="black")

        panel_w = int(w * 0.85)
        panel_h = int(h * 0.85)
        if panel_w < 600: panel_w = 600
        if panel_h < 500: panel_h = 500
        panel_x = (w - panel_w) // 2
        panel_y = (h - panel_h) // 2
        
        # The panel is an image with an alpha channel for transparency
        panel_img = Image.new("RGBA", (panel_w, panel_h), (24, 24, 27, 190)) # (R, G, B, Alpha)
        self.score_panel_photo = ImageTk.PhotoImage(panel_img)
        self.score_canvas.create_image(panel_x, panel_y, image=self.score_panel_photo, anchor="nw")

        self.score_canvas.create_window(w / 2, h / 2, window=self.score_widgets_frame, anchor="center")

    def show_error_screen(self):
        self.clear_screen()
        frame = tk.Frame(self.root)
        frame.pack(pady=80)
        tk.Label(frame, text="Error", font=("Arial", 18), fg="red").pack()
        tk.Label(frame, text=self.error_message or "Unknown error.", font=("Arial", 14), wraplength=500).pack(pady=10)
        tk.Button(frame, text="Back to Start", font=("Arial", 14), command=self.build_start_screen).pack(pady=20)
        self.current_screen = frame

    def clear_screen(self):
        if self.current_screen: 
            self.current_screen.destroy()
            self.current_screen = None

# --- Run the App ---
if __name__ == "__main__":
    root = tk.Tk()
    app = QuizApp(root)
    root.mainloop()
