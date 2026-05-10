import pandas as pd
import json
import os
from pathlib import Path

class TFIDFRecommender:
    def __init__(self, data_dir="recommendation/data"):
        self.data_dir = Path(data_dir)
        self.matrix_path = self.data_dir / "tfidf_matrix.parquet"
        self.weights_path = self.data_dir / "level_weights.json"
        
        self.df_tfidf = None
        self.level_weights = {}
        
        self.load_model()
        
    def load_model(self):
        if self.matrix_path.exists():
            self.df_tfidf = pd.read_parquet(self.matrix_path)
            self.df_tfidf.set_index('role', inplace=True)
            
        if self.weights_path.exists():
            with open(self.weights_path, 'r', encoding='utf-8') as f:
                self.level_weights = json.load(f)

    def query(self, target_role: str, user_skills: list, level: str = None, top_k: int = 10):
        if self.df_tfidf is None:
            return []
            
        target_role = target_role.lower().strip()
        user_skills = [s.lower().strip() for s in user_skills]
        
        try:
            role_skills = self.df_tfidf.loc[[target_role]]
        except KeyError:
            return []
            
        skills_scores = role_skills.reset_index()[['skill', 'score']].to_dict('records')
        
        results = []
        senior_weights = self.level_weights.get("senior", {})
        
        for item in skills_scores:
            skill = item['skill']
            score = item['score']
            
            if skill.lower() in user_skills:
                continue
                
            if level and level.lower() == 'senior':
                weight = senior_weights.get(skill, 1.0)
                score = score * weight
                
            results.append({"skill": skill, "score": score})
            
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

if __name__ == "__main__":
    recommender = TFIDFRecommender(data_dir="../data")
    print(recommender.query("data engineer", user_skills=["python"], level="senior", top_k=5))
