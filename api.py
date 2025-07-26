import logging
import asyncio
from llm.prompt import PromptGenerator
from llm.code_reviewer import CodeReviewLLM
from ingestion import ChromaDBIndexingService
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi import Depends

# Configure the root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


app = FastAPI()


class CodeReviewRequest(BaseModel):
    code: str
    project_name: str


class CodeReviewResponse(BaseModel):
    duplication_review: str
    style_review: str
    summary: str


def get_indexing_service(project_name: str = "code_repository"):
    return ChromaDBIndexingService(collection_name=project_name)


def get_prompt_generator():
    return PromptGenerator()


def get_code_reviewer():
    return CodeReviewLLM()


@app.post("/code-review", response_model=CodeReviewResponse)
async def review_code(
    request: CodeReviewRequest,
    prompt_generator: PromptGenerator = Depends(get_prompt_generator),
    code_reviewer: CodeReviewLLM = Depends(get_code_reviewer),
):
    code = request.code
    project_name = request.project_name

    indexing_service = get_indexing_service(project_name)

    if not code.strip():
        raise HTTPException(status_code=400, detail="Code snippet cannot be empty.")

    similar_code = indexing_service.query_code(code, n_results=5)
    logger.info("Generating review prompt for the provided code snippet.")
    review_prompt = prompt_generator.generate_coding_style_prompt(code)

    if not similar_code:
        logger.info("No similar code snippets found.")
        style_result = await code_reviewer.review(review_prompt)
        duplication_result = None
    else:
        logger.debug(f"Found {len(similar_code)} similar code snippets.")
        duplicate_code_check_prompt = prompt_generator.\
            generate_code_duplication_check_prompt(code, similar_code)

        duplication_result, style_result = await asyncio.gather(
            code_reviewer.review(duplicate_code_check_prompt),
            code_reviewer.review(review_prompt)
        )

    if not duplication_result:
        summary = style_result['response']
    else:
        summary = await code_reviewer.review(
            prompt_generator.generate_summary_prompt(
                style_result['response'], duplication_result['response']
            )
        )

    return CodeReviewResponse(
        duplication_review=duplication_result['response'] if duplication_result else "No duplication found.",
        style_review=style_result['response'] if style_result else "No style issues found.",
        summary=summary['response'] if summary else "No summary available."
    )
