from functools import lru_cache
from string import Template

from admin.config import TEMPLATE_DIR


@lru_cache(maxsize=1)
def render_index() -> bytes:
    layout = Template((TEMPLATE_DIR / "index.html").read_text(encoding="utf-8"))
    sections_dir = TEMPLATE_DIR / "sections"
    html = layout.substitute(
        login_section=(sections_dir / "login.html").read_text(encoding="utf-8"),
        accounts_section=(sections_dir / "accounts.html").read_text(encoding="utf-8"),
        clothes_section=(sections_dir / "clothes.html").read_text(encoding="utf-8"),
        profiles_section=(sections_dir / "profiles.html").read_text(encoding="utf-8"),
        pets_section=(sections_dir / "pets.html").read_text(encoding="utf-8"),
        pet_modal_section=(sections_dir / "pet-modal.html").read_text(encoding="utf-8"),
        house_goods_section=(sections_dir / "house-goods.html").read_text(encoding="utf-8"),
        actions_section=(sections_dir / "actions.html").read_text(encoding="utf-8"),
        account_modal_section=(sections_dir / "account-modal.html").read_text(encoding="utf-8"),
        clothing_modal_section=(sections_dir / "clothing-modal.html").read_text(encoding="utf-8"),
        profile_modal_section=(sections_dir / "profile-modal.html").read_text(encoding="utf-8"),
        profile_clothing_modal_section=(sections_dir / "profile-clothing-modal.html").read_text(encoding="utf-8"),
        house_goods_modal_section=(sections_dir / "house-goods-modal.html").read_text(encoding="utf-8"),
        action_modal_section=(sections_dir / "action-modal.html").read_text(encoding="utf-8"),
        flowers_section=(sections_dir / "flowers.html").read_text(encoding="utf-8"),
        seeds_section=(sections_dir / "seeds.html").read_text(encoding="utf-8"),
        materials_section=(sections_dir / "materials.html").read_text(encoding="utf-8"),
        pet_supplies_section=(sections_dir / "pet-supplies.html").read_text(encoding="utf-8"),
        gardens_section=(sections_dir / "gardens.html").read_text(encoding="utf-8"),
        garden_modal_section=(sections_dir / "garden-modal.html").read_text(encoding="utf-8"),
        inventory_modal_section=(sections_dir / "inventory-modal.html").read_text(encoding="utf-8"),
        tools_section=(sections_dir / "tools.html").read_text(encoding="utf-8"),
        pollens_section=(sections_dir / "pollens.html").read_text(encoding="utf-8"),
        houses_section=(sections_dir / "houses.html").read_text(encoding="utf-8"),
        tasks_section=(sections_dir / "tasks.html").read_text(encoding="utf-8"),
    )
    return html.encode("utf-8")
