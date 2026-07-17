from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.services import get_review_repository
from app.domain.ports import ReviewRepository
from app.schemas.reviews import PullRequestReviewDetailSchema, PullRequestReviewSchema

router = APIRouter()


@router.get(
    "/reviews",
    response_model=list[PullRequestReviewSchema],
    status_code=status.HTTP_200_OK,
)
async def list_reviews(
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
) -> list[PullRequestReviewSchema]:
    reviews = await repository.list_reviews()
    return [PullRequestReviewSchema.model_validate(r) for r in reviews]


@router.get(
    "/reviews/{review_id}",
    response_model=PullRequestReviewDetailSchema,
    status_code=status.HTTP_200_OK,
)
async def get_review(
    review_id: str,
    repository: Annotated[ReviewRepository, Depends(get_review_repository)],
) -> PullRequestReviewDetailSchema:
    review = await repository.get_review(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with ID {review_id} not found.",
        )

    tasks = await repository.get_tasks(review_id)

    return PullRequestReviewDetailSchema(
        id=review.id,
        repository=review.repository,
        pull_request_number=review.pull_request_number,
        delivery_id=review.delivery_id,
        status=review.status,
        score=review.score,
        security_score=review.security_score,
        performance_score=review.performance_score,
        architecture_score=review.architecture_score,
        documentation_score=review.documentation_score,
        created_at=review.created_at,
        updated_at=review.updated_at,
        tasks=tasks,
    )
