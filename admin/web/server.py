from http.server import ThreadingHTTPServer

from admin.core.sessions import SessionStore
from admin.web.handler import AdminHandler


class AdminServer(ThreadingHTTPServer):
    def __init__(self, address, accounts, clothes, profiles, house_goods, actions, flowers, seeds, materials, gardens, pets, pet_supplies, tools, pollens, houses, tasks):
        super().__init__(address, AdminHandler)
        self.accounts = accounts
        self.clothes = clothes
        self.profiles = profiles
        self.house_goods = house_goods
        self.actions = actions
        self.flowers = flowers
        self.seeds = seeds
        self.materials = materials
        self.gardens = gardens
        self.pets = pets
        self.pet_supplies = pet_supplies
        self.tools = tools
        self.pollens = pollens
        self.houses = houses
        self.tasks = tasks
        self.sessions = SessionStore()
