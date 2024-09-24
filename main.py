import streamlit as st
from openai import OpenAI
import json
import time
import random

client = OpenAI(api_key=st.secrets["OPEN_AI_KEY"])


# Question class to store details of each question
class Question:
    def __init__(self, question, options, correct_answer, explanation=None):
        self.question = question
        self.options = options
        self.correct_answer = correct_answer
        self.explanation = explanation


# Quiz class to manage quiz state and interactions
class Quiz:
    def __init__(self):
        self.questions = self.load_or_generate_questions()
        self.initialize_session_state()

    def load_or_generate_questions(self):
        # Check if questions already exist in the session state
        if 'questions' not in st.session_state:
            # Predefined questions or load from a source
            st.session_state.questions = [
                Question("What is the capital of France?", ["London", "Paris", "Berlin", "Madrid"], "Paris",
                         "Paris is the capital and most populous city of France."),
                Question("Who developed the theory of relativity?",
                         ["Isaac Newton", "Albert Einstein", "Nikola Tesla", "Marie Curie"], "Albert Einstein",
                         "Albert Einstein is known for developing the theory of relativity, one of the two pillars of modern physics.")
            ]

        return st.session_state.questions

    # Initialize session variables if not already set
    def initialize_session_state(self):
        if 'current_question_index' not in st.session_state:
            st.session_state.current_question_index = 0
        if 'score' not in st.session_state:
            st.session_state.score = 0
        if 'answers_submitted' not in st.session_state:
            st.session_state.answers_submitted = 0  # Track the number of answers submitted

    # Display the quiz questions or results based on progress
    def display_quiz(self):
        self.update_progress_bar()
        if st.session_state.answers_submitted >= len(self.questions):
            self.display_results()
        else:
            self.display_current_question()

    # Display the current question with options
    def display_current_question(self):
        question = self.questions[st.session_state.current_question_index]
        st.write(question.question)
        options = question.options
        # Generate a radio button for options, use unique key to avoid state conflicts
        answer = st.radio("Choose one:", options, key=f"question_{st.session_state.current_question_index}")
        if st.button("Submit Answer", key=f"submit_{st.session_state.current_question_index}"):
            self.check_answer(answer)
            st.session_state.answers_submitted += 1
            # Move to the next question after submission
            if st.session_state.current_question_index < len(self.questions) - 1:
                st.session_state.current_question_index += 1
            st.rerun()

    # Check if the selected answer is correct and update the score
    def check_answer(self, user_answer):
        correct_answer = self.questions[st.session_state.current_question_index].correct_answer
        if user_answer == correct_answer:
            st.session_state.score += 1
            # Show explanation if provided
            if self.questions[st.session_state.current_question_index].explanation:
                st.info(self.questions[st.session_state.current_question_index].explanation)
            time.sleep(1.5) # Delay for user to read explanation
        else:
            st.error("Wrong answer!")
            time.sleep(0.5)

    # Display the quiz results after completion
    def display_results(self):
        st.write(f"Quiz completed! Your score: {st.session_state.score}/{len(self.questions)}")
        # Provide feedback based on score
        if st.session_state.score/len(self.questions) == 1.0:
            st.success("Congrats")
            st.balloons()
        else:
            st.error("You failed, try again!")

        # Option to show correct answers or retake the quiz
        if st.button("Show Answers"):
            history = quiz_history()
            show_answers(history)

        if st.button("Retake Quiz"):
            self.restart_quiz()

    # Update the progress bar based on answered questions
    def update_progress_bar(self):
        total_questions = len(self.questions)
        progress = st.session_state.answers_submitted / total_questions
        st.progress(progress)

    # Restart the quiz by resetting the session state and reshuffling questions
    def restart_quiz(self):
        st.session_state.current_question_index = 0
        st.session_state.score = 0
        st.session_state.answers_submitted = 0
        random.shuffle(st.session_state.questions)
        st.rerun()


# Function to track quiz history (questions and correct answers)
def quiz_history():
    history_dict = {
        'questions': [],
        'answers': [],
    }
    for q in st.session_state.questions:
        history_dict.get('questions').append(q.question)
        history_dict.get('answers').append(q.correct_answer)
    return history_dict


# Function to display correct answers in a dialog
@st.dialog("Answers", width="large")
def show_answers(history):
    num_questions = len(history['questions'])
    for index, (question, answer) in enumerate(zip(history['questions'], history['answers'])):
        st.write(f"**Question:**  {question}")
        st.write(f"**Answer:**  {answer}")

        # Add separator only if it's not the last question
        if index < num_questions - 1:
            st.write("***")


# Function to generate a new question using GPT and append it to the quiz
def generate_and_append_question(user_prompt):
    history = quiz_history()

    gpt_prompt = '''Generate a JSON response for a trivia question including the question, options, correct answer, and explanation. The format should be as follows:

{
  "Question": "The actual question text goes here?",
  "Options": ["Option1", "Option2", "Option3", "Option4"],
  "CorrectAnswer": "TheCorrectAnswer",
  "Explanation": "A detailed explanation on why the correct answer is correct."
}'''
    try:
        # Generate question using GPT model
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": gpt_prompt},
                {"role": "user", "content": f"Create a question about : {user_prompt} that is different from those : {history}"}
            ]
        )
        gpt_response = json.loads(response.choices[0].message.content)  # Assuming this returns the correct JSON structure
        new_question = Question(
            question=gpt_response["Question"],
            options=gpt_response["Options"],
            correct_answer=gpt_response["CorrectAnswer"],
            explanation=gpt_response["Explanation"]
        )
        st.session_state.questions.append(new_question)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")


# Function to edit the quiz and delete questions
@st.dialog("Edit Quiz", width='large')
def edit_quiz():
    for i, question in enumerate(st.session_state.questions):
        col1, col2 = st.columns(2, vertical_alignment='center')

        with col1:
            st.subheader(f"Question {i + 1}")
            st.write(question.question)
        with col2:
            # Allow deletion of questions, ensuring at least one question remains
            if st.button(f"Delete Question {i + 1}", key=f"delete_btn_{i}", disabled=len(st.session_state.questions) == 1):
                del st.session_state.questions[i]
                st.rerun()


# Main function to control the application
def main():
    # Initialize quiz if not already done
    if 'quiz_initialized' not in st.session_state:
        st.session_state.quiz = Quiz()
        st.session_state.quiz_initialized = True

    st.title("Create your own Quiz with the power of AI!")

    user_input = st.text_input("Add your preferences", placeholder="e.g. history, biology, technology...")

    is_disabled = st.session_state.answers_submitted > 0

    col1, col2 = st.columns(2, gap="small")

    with col1:
        if st.button('Generate New Question', disabled=st.session_state.answers_submitted > 0):
            generate_and_append_question(user_input)

    with col2:
        if st.button("Edit Quiz", disabled=st.session_state.answers_submitted > 0):
            edit_quiz()

    if is_disabled:
        st.info("This action is not supported while the quiz is in session.", icon="🚨")

    st.session_state.quiz.display_quiz()


if __name__ == "__main__":
    main()
