import chromadb
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()
KNOWLEDGE_DIR = Path(settings.KNOWLEDGE_DIR)
CHROMA_DIR = Path(settings.CHROMA_PERSIST_DIR)


def build_chroma_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name="ad_cases",
        metadata={"description": "广告违规行政处罚案例库"},
    )

    existing = collection.count()
    if existing > 0:
        print(f"ChromaDB already has {existing} cases, skipping ingestion.")
        return

    cases_dir = KNOWLEDGE_DIR / "L3_cases"
    docs, metadatas, ids = [], [], []

    for case_file in sorted(cases_dir.rglob("*.txt")):
        text = case_file.read_text(encoding="utf-8")
        title = text.split("\n")[0].strip()[:200]
        province = case_file.parent.name
        # Make doc_id unique by including the top-level category (按省份/按行业/按违规类型)
        rel = case_file.relative_to(cases_dir)
        doc_id = str(rel.with_suffix("")).replace("\\", "/")[:60]

        docs.append(text)
        metadatas.append(
            {
                "title": title,
                "province": province,
                "source": str(case_file.relative_to(KNOWLEDGE_DIR)),
            }
        )
        ids.append(doc_id)

    if docs:
        collection.add(documents=docs, metadatas=metadatas, ids=ids)
        print(f"ChromaDB: ingested {len(docs)} cases.")


if __name__ == "__main__":
    build_chroma_collection()
