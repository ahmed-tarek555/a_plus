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

    @root_validator
    def validate_choice_fields(cls, values):
        is_choices = values.get("is_choices")
        choices = values.get("choices")
        correct_choice = values.get("correct_choice")

        if is_choices:
            if not choices or len(choices) < 2:
                raise ValueError("Multiple choice questions need at least 2 choices")
            choice_texts = [c.text for c in choices]
            if correct_choice not in choice_texts:
                raise ValueError("correct_choice must match one of the choices")
        else:
            if choices or correct_choice is not None:
                raise ValueError("Text questions should not include choices or correct_choice")

        return values


class ExamCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    questions: List[QuestionCreate] = []


# example payload
# {
#   "title": "Chapter 3 Quiz",
#   "description": "Covers photosynthesis",
#   "due_date": "2026-08-01T23:59:00",
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
#       "mark": 5
#     }
#   ]
# }