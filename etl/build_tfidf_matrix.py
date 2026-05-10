import pandas as pd
import numpy as np
import os
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path

def build_tfidf_model():
    print("1. Đọc dữ liệu Silver data...")
    local_path = "silver_jobs_cleaned_local.csv"
    if not os.path.exists(local_path):
        print(f"[Lỗi] Không tìm thấy {local_path}. Vui lòng chạy lại etl/bronze_to_silver.py trước.")
        return
        
    df = pd.read_csv(local_path).dropna(subset=['job_title', 'job_skills'])
    
    # Đảm bảo job_skills là string
    df['job_skills'] = df['job_skills'].astype(str)
    
    print("2. Tính toán Level-Weighting (Senior vs Junior)...")
    # Định nghĩa pattern
    senior_pattern = r'\bsenior\b|\blead\b|\bprincipal\b|\bsr\b'
    junior_pattern = r'\bjunior\b|\bintern\b|\bfresher\b|\btrainee\b|\bjr\b'
    
    is_senior = df['job_title'].str.contains(senior_pattern, case=False, na=False)
    is_junior = df['job_title'].str.contains(junior_pattern, case=False, na=False)
    
    total_senior = is_senior.sum()
    total_junior = is_junior.sum()
    
    senior_skills = df[is_senior]['job_skills'].str.split(',').explode().str.strip()
    junior_skills = df[is_junior]['job_skills'].str.split(',').explode().str.strip()
    
    senior_counts = senior_skills.value_counts()
    junior_counts = junior_skills.value_counts()
    
    all_skills = set(senior_counts.index).union(set(junior_counts.index))
    senior_weights = {}
    
    # Smoothing để tránh chia 0
    alpha = 1
    for skill in all_skills:
        s_c = senior_counts.get(skill, 0)
        j_c = junior_counts.get(skill, 0)
        
        # P(skill | senior)
        p_senior = (s_c + alpha) / (total_senior + alpha * 2) if total_senior > 0 else 0
        # P(skill | junior)
        p_junior = (j_c + alpha) / (total_junior + alpha * 2) if total_junior > 0 else 0
        
        if p_junior > 0:
            ratio = p_senior / p_junior
            # Giới hạn weight từ 0.5 đến 3.0 để tránh over-weighting
            weight = max(0.5, min(ratio, 3.0))
            senior_weights[skill] = weight
        else:
            senior_weights[skill] = 1.0
            
    print("3. Tính toán TF-IDF score cho từng role...")
    # Group theo job_title (mỗi role là 1 document)
    grouped = df.groupby('job_title')['job_skills'].apply(lambda x: ','.join(x)).reset_index()
    
    def skill_tokenizer(text):
        return [s.strip() for s in text.split(',') if s.strip()]
        
    vectorizer = TfidfVectorizer(tokenizer=skill_tokenizer, token_pattern=None, lowercase=False)
    tfidf_matrix = vectorizer.fit_transform(grouped['job_skills'])
    
    skills = vectorizer.get_feature_names_out()
    coo = tfidf_matrix.tocoo()
    roles = grouped['job_title'].values
    
    # Chuyển đổi thành DataFrame
    df_tfidf = pd.DataFrame({
        'role': roles[coo.row],
        'skill': skills[coo.col],
        'score': coo.data
    })
    
    # Lọc các skill có score quá thấp (giảm dung lượng matrix)
    df_tfidf = df_tfidf[df_tfidf['score'] > 0.01]
    
    # Sắp xếp để query nhanh hơn
    df_tfidf = df_tfidf.sort_values(by=['role', 'score'], ascending=[True, False])
    
    print("4. Lưu model ra file (parquet & json)...")
    out_dir = Path("recommendation/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    parquet_path = out_dir / "tfidf_matrix.parquet"
    weights_path = out_dir / "level_weights.json"
    
    df_tfidf.to_parquet(parquet_path, index=False)
    with open(weights_path, 'w', encoding='utf-8') as f:
        json.dump({"senior": senior_weights}, f, ensure_ascii=False, indent=2)
        
    print(f"Xong! Đã lưu TF-IDF Matrix (Shape: {df_tfidf.shape}) tại: {parquet_path}")
    print(f"Level Weights đã lưu tại: {weights_path}")

if __name__ == "__main__":
    build_tfidf_model()
