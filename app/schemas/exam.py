from pydantic import BaseModel, root_validator
from typing import Optional, List
from datetime import datetime


class ChoiceCreate(BaseModel):
    text: str


class QuestionCreate(BaseModel):
    is_choices: bool
    head: str
    mark: int
    choices: Optional[List[ChoiceCreate]] = None
    correct_choice: Optional[str] = None
    model_answer: Optional[str] = None

    @root_validator
    def validate_choice_fields(cls, values):
        is_choices = values.get("is_choices")
        choices = values.get("choices")
        correct_choice = values.get("correct_choice")
        model_answer = values.get("model_answer")

        if is_choices:
            if not choices or len(choices) < 2:
                raise ValueError("Multiple choice questions need at least 2 choices")
            choice_texts = [c.text for c in choices]
            if correct_choice not in choice_texts:
                raise ValueError("correct choice must match one of the choices")
        else:
            if choices or correct_choice is not None:
                raise ValueError("Text questions should not include choices or correct_choice")
            if not model_answer:
                raise ValueError("Text questions should include the model answer")

        return values


class ExamCreate(BaseModel):
    title: str
    start_time: datetime
    time: int
    questions: List[QuestionCreate] = []

class AnswerSubmit(BaseModel):
    question_id: int
    answer: str

class ExamSubmit(BaseModel):
    answers: List[AnswerSubmit]

# example payload
# {
#   "title": "Chapter 3 Quiz",
#   "start_time": "2026-08-01T23:59:00",
#   "time": 2
#   "questions": [
#     {
#       "is_choices": true,
#       "head": "What is 2 + 2?",
#       "mark": 1,
#       "choices": [{"text": "3"}, {"text": "4"}, {"text": "5"}],
#       "correct_choice": "4"
#     },
#     {
#       "is_choices": false,
#       "head": "Explain photosynthesis.",
#       "model_answer": "the answer the teacher entered"
#       "mark": 5
#     }
#   ]
# }