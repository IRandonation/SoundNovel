from models import World, Plot, Chapter
from utils import load_prompt, call_api, load_config
import json

class WorldGenerator:
    @staticmethod
    def generate(initial_prompt):
        config = load_config()
        prompt = load_prompt("world")
        params = config["generation"]["world"]
        
        response = call_api(
            prompt=initial_prompt,
            system_msg=prompt,
            temp=params["temperature"],
            max_tokens=params["max_tokens"]
        )
        return World(**json.loads(response))

class PlotGenerator:
    @staticmethod
    def generate(world):
        config = load_config()
        prompt = load_prompt("plot")
        params = config["generation"]["plot"]
        
        response = call_api(
            prompt=json.dumps(world.__dict__),
            system_msg=prompt,
            temp=params["temperature"],
            max_tokens=params["max_tokens"]
        )
        return Plot(**json.loads(response))

class ChapterGenerator:
    @staticmethod
    def generate(outline, previous_chapters):
        config = load_config()
        prompt = load_prompt("chapter")
        params = config["generation"]["chapter"]
        
        input_data = {
            "outline": outline,
            "previous": [ch.__dict__ for ch in previous_chapters]
        }
        
        response = call_api(
            prompt=json.dumps(input_data),
            system_msg=prompt,
            temp=params["temperature"],
            max_tokens=params["max_tokens"]
        )
        return Chapter(**json.loads(response))