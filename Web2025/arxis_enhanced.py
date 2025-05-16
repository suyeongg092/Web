import requests
from bs4 import BeautifulSoup
import csv
import re
import time
from tqdm import tqdm

BASE_URL = "https://arxiv.org"
LIST_URL = f"{BASE_URL}/list/cs.CR/recent"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ArxivWebCrawler/3.0)"
}

def clean(text):
    """텍스트 정제: LaTeX, placeholder 제거"""
    if not text:
        return ""
    text = re.sub(r'\\href\{.*?\}\{.*?\}', '', text)
    text = re.sub(r'\\href\{\}', '', text)
    return text.replace("this https URL", "").replace("{https URL}", "").strip()

def fetch_abstract(abs_url):
    """논문 상세 페이지에서 abstract만 수집"""
    try:
        res = requests.get(abs_url, headers=HEADERS)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        abstract_tag = soup.find("blockquote", class_="abstract")
        abstract = clean(abstract_tag.text.replace("Abstract:", "").strip()) if abstract_tag else ""
        return abstract
    except Exception as e:
        print(f"[!] {abs_url} abstract 수집 실패: {e}")
        return ""

def scrape_arxiv_optimized():
    res = requests.get(LIST_URL, headers=HEADERS)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    dl = soup.find("dl")
    dts = dl.find_all("dt")
    dds = dl.find_all("dd")

    print("[*] 논문 수집 시작...")
    results = []

    for dt, dd in tqdm(zip(dts, dds), total=len(dts), desc="논문 수집", ncols=80):
        abs_tag = dt.find("a", title="Abstract")
        if not abs_tag:
            continue

        paper_id = abs_tag.text.strip()
        abs_url = BASE_URL + abs_tag['href']

        title_tag = dd.find("div", class_="list-title mathjax")
        title = clean(title_tag.text.replace("Title:", "").strip()) if title_tag else ""

        authors_tag = dd.find("div", class_="list-authors")
        authors = clean(authors_tag.text.replace("Authors:", "").strip()) if authors_tag else ""

        subjects_tag = dd.find("div", class_="list-subjects")
        subjects = clean(subjects_tag.text.replace("Subjects:", "").strip()) if subjects_tag else ""

        pdf_tag = dt.find("a", href=lambda x: x and x.startswith("/pdf/"))
        pdf_url = BASE_URL + pdf_tag["href"] + ".pdf" if pdf_tag else ""

        html_tag = dt.find("a", href=lambda x: x and "html" in x)
        html_url = html_tag["href"] if html_tag else ""

        other_tag = dt.find("a", href=lambda x: x and "/format/" in x)
        other_url = BASE_URL + other_tag["href"] if other_tag else ""

        abstract = fetch_abstract(abs_url)
        time.sleep(1.2)

        if not abstract or "available at" in abstract.lower():
            continue

        results.append({
            "id": paper_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "subjects": subjects,
            "abs_url": abs_url,
            "pdf_url": pdf_url,
            "html_url": html_url,
            "other_formats_url": other_url
        })

    # 제목 기준 중복 제거
    seen = set()
    unique = []
    for r in results:
        if r["title"] not in seen:
            seen.add(r["title"])
            unique.append(r)
    return unique

def save_csv(data, filename="arxiv__cr.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"[+] {filename} 저장 완료 ({len(data)}개 논문)")

if __name__ == "__main__":
    data = scrape_arxiv_optimized()
    if data:
        save_csv(data)
    else:
        print("[!] 유효한 논문이 없습니다.")
