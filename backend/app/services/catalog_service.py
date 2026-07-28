from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, conflict, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.models.subcategory import SubCategory
from app.models.user import User
from app.repositories.catalog import BrandRepository, CategoryRepository, SubCategoryRepository
from app.schemas.brand import BrandCreate, BrandUpdate
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.subcategory import SubCategoryCreate, SubCategoryUpdate


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CategoryRepository(db)

<<<<<<< HEAD
    @staticmethod
    def _store_id(current_user: User) -> UUID:
        if not current_user.store_id:
            raise bad_request("Current user is not assigned to a store")
        return current_user.store_id

    def list(self, current_user: User, skip: int = 0, limit: int = 100) -> list[Category]:
        return self.repo.list_hierarchy(self._store_id(current_user), skip, limit)

    def list_hierarchy(self, current_user: User, skip: int = 0, limit: int = 100) -> list[Category]:
        return self.repo.list_hierarchy(self._store_id(current_user), skip, limit)

    def get(self, category_id: UUID, current_user: User) -> Category:
        category = self.repo.get(category_id)
        if not category or category.store_id != self._store_id(current_user):
=======
    def list(self, current_user: User, skip: int = 0, limit: int = 100) -> list[Category]:
        return self.repo.list_for_store(_store_id(current_user), skip, limit)

    def list_hierarchy(self, current_user: User, skip: int = 0, limit: int = 100) -> list[Category]:
        return self.repo.list_hierarchy(_store_id(current_user), skip, limit)

    def get(self, category_id: UUID, current_user: User) -> Category:
        category = self.repo.get_for_store(category_id, _store_id(current_user))
        if not category:
>>>>>>> shop-inventory
            raise not_found("Category")
        return category

    def create(self, payload: CategoryCreate, current_user: User) -> Category:
<<<<<<< HEAD
        store_id = self._store_id(current_user)
=======
        store_id = _store_id(current_user)
>>>>>>> shop-inventory
        if self.repo.get_by_name(store_id, payload.name):
            raise conflict("Category already exists")
        category = Category(store_id=store_id, **payload.model_dump())
        self.repo.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(self, category_id: UUID, payload: CategoryUpdate, current_user: User) -> Category:
<<<<<<< HEAD
        category = self.get(category_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            duplicate = self.repo.get_by_name(self._store_id(current_user), data["name"])
=======
        store_id = _store_id(current_user)
        category = self.get(category_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            duplicate = self.repo.get_by_name(store_id, data["name"])
>>>>>>> shop-inventory
            if duplicate and duplicate.id != category.id:
                raise conflict("Category already exists")
        for key, value in data.items():
            setattr(category, key, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category_id: UUID, current_user: User) -> None:
        category = self.get(category_id, current_user)
        if self.repo.product_count(category_id) > 0:
            raise bad_request("Category is used by products and cannot be deleted")
        self.repo.delete(category)
        self.db.commit()


class BrandService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = BrandRepository(db)

    def list(self, current_user: User, category_id: UUID | None = None, skip: int = 0, limit: int = 100) -> list[Brand]:
<<<<<<< HEAD
        return self.repo.list_by_category(CategoryService._store_id(current_user), category_id, skip, limit)

    def get(self, brand_id: UUID, current_user: User) -> Brand:
        brand = self.repo.get(brand_id)
        if not brand or brand.store_id != CategoryService._store_id(current_user):
=======
        return self.repo.list_by_category(_store_id(current_user), category_id, skip, limit)

    def get(self, brand_id: UUID, current_user: User) -> Brand:
        brand = self.repo.get_for_store(brand_id, _store_id(current_user))
        if not brand:
>>>>>>> shop-inventory
            raise not_found("Brand")
        return brand

    def create(self, payload: BrandCreate, current_user: User) -> Brand:
<<<<<<< HEAD
        store_id = CategoryService._store_id(current_user)
        category = self.db.get(Category, payload.category_id)
        if not category or category.store_id != store_id:
=======
        store_id = _store_id(current_user)
        if not self.db.query(Category).filter(Category.id == payload.category_id, Category.store_id == store_id).first():
>>>>>>> shop-inventory
            raise not_found("Category")
        if self.repo.get_by_name(store_id, payload.category_id, payload.name):
            raise conflict("Brand already exists in this category")
        brand = Brand(store_id=store_id, **payload.model_dump())
        self.repo.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def update(self, brand_id: UUID, payload: BrandUpdate, current_user: User) -> Brand:
<<<<<<< HEAD
=======
        store_id = _store_id(current_user)
>>>>>>> shop-inventory
        brand = self.get(brand_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        next_category_id = data.get("category_id", brand.category_id)
        if next_category_id != brand.category_id and self.repo.product_count(brand.id):
            raise bad_request("Brand category cannot change while products use it")
<<<<<<< HEAD
        category = self.db.get(Category, next_category_id)
        if not category or category.store_id != CategoryService._store_id(current_user):
            raise not_found("Category")
        if "name" in data or "category_id" in data:
            duplicate = self.repo.get_by_name(CategoryService._store_id(current_user), next_category_id, data.get("name", brand.name))
=======
        if not self.db.query(Category).filter(Category.id == next_category_id, Category.store_id == store_id).first():
            raise not_found("Category")
        if "name" in data or "category_id" in data:
            duplicate = self.repo.get_by_name(store_id, next_category_id, data.get("name", brand.name))
>>>>>>> shop-inventory
            if duplicate and duplicate.id != brand.id:
                raise conflict("Brand already exists in this category")
        for key, value in data.items():
            setattr(brand, key, value)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def delete(self, brand_id: UUID, current_user: User) -> None:
        brand = self.get(brand_id, current_user)
        if self.repo.product_count(brand_id) > 0:
            raise bad_request("Brand is used by products and cannot be deleted")
        self.repo.delete(brand)
        self.db.commit()


class SubCategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SubCategoryRepository(db)

    def list(self, current_user: User, category_id: UUID | None = None, skip: int = 0, limit: int = 100) -> list[SubCategory]:
<<<<<<< HEAD
        return self.repo.list_by_category(CategoryService._store_id(current_user), category_id, skip, limit)

    def get(self, subcategory_id: UUID, current_user: User) -> SubCategory:
        subcategory = self.repo.get(subcategory_id)
        if not subcategory or subcategory.store_id != CategoryService._store_id(current_user):
=======
        return self.repo.list_by_category(_store_id(current_user), category_id, skip, limit)

    def get(self, subcategory_id: UUID, current_user: User) -> SubCategory:
        subcategory = self.repo.get_for_store(subcategory_id, _store_id(current_user))
        if not subcategory:
>>>>>>> shop-inventory
            raise not_found("Subcategory")
        return subcategory

    def create(self, payload: SubCategoryCreate, current_user: User) -> SubCategory:
<<<<<<< HEAD
        store_id = CategoryService._store_id(current_user)
        category = self.db.get(Category, payload.category_id)
        if not category or category.store_id != store_id:
=======
        store_id = _store_id(current_user)
        if not self.db.query(Category).filter(Category.id == payload.category_id, Category.store_id == store_id).first():
>>>>>>> shop-inventory
            raise not_found("Category")
        if self.repo.get_by_name(store_id, payload.category_id, payload.name):
            raise conflict("Subcategory already exists in this category")
        subcategory = SubCategory(store_id=store_id, **payload.model_dump())
        self.repo.add(subcategory)
        self.db.commit()
        self.db.refresh(subcategory)
        return subcategory

    def update(self, subcategory_id: UUID, payload: SubCategoryUpdate, current_user: User) -> SubCategory:
<<<<<<< HEAD
=======
        store_id = _store_id(current_user)
>>>>>>> shop-inventory
        subcategory = self.get(subcategory_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        next_category_id = data.get("category_id", subcategory.category_id)
        if next_category_id != subcategory.category_id and self.repo.product_count(subcategory.id):
            raise bad_request("Subcategory cannot move while products use it")
<<<<<<< HEAD
        category = self.db.get(Category, next_category_id)
        if not category or category.store_id != CategoryService._store_id(current_user):
            raise not_found("Category")
        duplicate = self.repo.get_by_name(CategoryService._store_id(current_user), next_category_id, data.get("name", subcategory.name))
=======
        if not self.db.query(Category).filter(Category.id == next_category_id, Category.store_id == store_id).first():
            raise not_found("Category")
        duplicate = self.repo.get_by_name(store_id, next_category_id, data.get("name", subcategory.name))
>>>>>>> shop-inventory
        if duplicate and duplicate.id != subcategory.id:
            raise conflict("Subcategory already exists in this category")
        for key, value in data.items():
            setattr(subcategory, key, value)
        self.db.commit()
        self.db.refresh(subcategory)
        return subcategory

    def delete(self, subcategory_id: UUID, current_user: User) -> None:
        subcategory = self.get(subcategory_id, current_user)
        if self.repo.product_count(subcategory_id):
            raise bad_request("Subcategory is used by products and cannot be deleted")
        self.repo.delete(subcategory)
        self.db.commit()


def _store_id(current_user: User) -> UUID:
    if current_user.store_id is None:
        raise bad_request("Current user is not assigned to a store")
    return current_user.store_id
