from sqlalchemy.orm import Session
from models import models
from schemas import webtoon_schemas, user_schemas
from datetime import datetime
from fastapi import HTTPException
from util import background_util, pose_util


def get_webtoon_by_webtoon_name_and_userId(db: Session, webtoon_name: str, user_id: int):
    return db.query(models.Webtoon).filter(models.Webtoon.webtoonName == webtoon_name,
                                           models.Webtoon.userId == user_id
                                           ).first()

def get_webtoon_list_by_user_id(db: Session, userId: int):
    return db.query(models.Webtoon).filter(models.Webtoon.userId == userId).all()

def create_webtoon(db: Session, webtoon: webtoon_schemas.WebtoonCreate, user: user_schemas.TokenData):
    if get_webtoon_by_webtoon_name_and_userId(db, webtoon_name=webtoon.webtoonName, user_id=user['userId']):
        raise HTTPException(status_code=400, detail="Bad Request: Webtoon already registered")
    db_webtoon = models.Webtoon(webtoonName=webtoon.webtoonName,
                                userId=user['userId'],
                                createdAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                )
    if db_webtoon is None:
        raise HTTPException(status_code=404, detail="Failed to create webtoon")
    try:
        db.add(db_webtoon)
        db.commit()
        db.refresh(db_webtoon)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    return {"message": "Webtoon created successfully"}

def read_webtoon_list(db: Session, userId: int):
    webtoons = get_webtoon_list_by_user_id(db, userId)
    if webtoons is None:
        raise HTTPException(status_code=404, detail="Webtoon not found")
    formatted_webtoons = []
    for webtoon in webtoons:
        formatted_webtoons.append(webtoon.webtoonName)
    return {"webtoonList":formatted_webtoons}

def check_train(db: Session, webtoon_name: str, user_id: int):
    db_model = db.query(models.Model)\
        .join(models.Webtoon, models.Model.webtoonId == models.Webtoon.id)\
        .filter(models.Webtoon.webtoonName == webtoon_name)\
        .filter(models.Webtoon.userId == user_id)\
        .first()
    if db_model and db_model.modelPath:
        return {"isTrained": True}
    else:
        return {"isTrained": False}

def delete_webtoon(db: Session, webtoon_name: str, user_id: int):
    db_webtoon = get_webtoon_by_webtoon_name_and_userId(db, webtoon_name=webtoon_name, user_id=user_id)
    if db_webtoon:
        db_content_img = db.query(models.ContentImg).filter(models.ContentImg.webtoonId == db_webtoon.id).all()
        db_pose_img = db.query(models.PoseImg).filter(models.PoseImg.webtoonId == db_webtoon.id).all()
        db_model = db.query(models.Model).filter(models.Model.webtoonId == db_webtoon.id).all()
        if db_content_img:
            for db_content_imgs in db_content_img:
                background_util.delete_content_asset(webtoon_name=webtoon_name, asset_name=db_content_imgs.assetName, db=db, user_id=user_id)
        if db_pose_img:
            for db_pose_imgs in db_pose_img:
                pose_util.delete_pose_asset(webtoon_name=webtoon_name, asset_name=db_pose_imgs.assetName, db=db, user_id=user_id)
        if db_model:
            try:
                for db_models in db_model:
                    db.delete(db_models)
                db.commit()
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Internal Server Error")
        try:
            db.delete(db_webtoon)
            db.commit()
            return {"message": "Webtoon deleted successfully"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail="Internal Server Error")
    else:
        raise HTTPException(status_code=400, detail="Bad Request: Webtoon not found")