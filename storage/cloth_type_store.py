from typing import Dict, Iterable, Mapping


class ClothTypeStore:
    """In-memory ``type_clothes.id -> cloth_type`` catalog.

    The catalog is loaded once when AccountStore is created.  Keeping the
    database query here avoids querying the reference table for every 1018
    clothing change request.
    """

    def __init__(self, cloth_types: Mapping[int, int]):
        self._cloth_types: Dict[int, int] = dict(cloth_types)

    @classmethod
    def load(cls, connection) -> "ClothTypeStore":
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, cloth_type FROM type_clothes")
            rows: Iterable[Mapping[str, object]] = cursor.fetchall() or []
        values = {}
        for row in rows:
            try:
                values[int(row["id"])] = int(row["cloth_type"])
            except (KeyError, TypeError, ValueError):
                continue
        return cls(values)

    def get(self, cloth_id: int):
        try:
            return self._cloth_types.get(int(cloth_id))
        except (TypeError, ValueError):
            return None

    def __len__(self) -> int:
        return len(self._cloth_types)
    