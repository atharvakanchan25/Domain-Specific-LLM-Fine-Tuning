"""
knowledge-graph/pipelines/entity_extractor.py
Extracts entities and relationships from parsed text using spaCy + heuristics.
Run standalone: python entity_extractor.py --text "..." 
"""
from __future__ import annotations
import re
import spacy
from dataclasses import dataclass

nlp = spacy.load("en_core_web_sm")

SERVICE_PATTERNS = re.compile(
    r'\b([A-Z][a-zA-Z]+(?:Service|Manager|Handler|Controller|Client|API|Gateway|Worker))\b'
)
DEPENDENCY_VERBS = {"depends on", "calls", "uses", "imports", "requires", "connects to"}
EVENT_VERBS      = {"publishes", "emits", "produces", "sends"}
CONSUME_VERBS    = {"consumes", "subscribes to", "listens to", "reads from"}


@dataclass
class Entity:
    name: str
    label: str
    properties: dict


@dataclass
class Relation:
    from_name: str
    from_label: str
    to_name: str
    to_label: str
    rel_type: str
    props: dict


def extract(text: str) -> tuple[list[Entity], list[Relation]]:
    entities: list[Entity] = []
    relations: list[Relation] = []
    seen_entities: set[str] = set()

    # Extract service names via regex
    for match in SERVICE_PATTERNS.finditer(text):
        name = match.group(1)
        if name not in seen_entities:
            entities.append(Entity(name=name, label="Service", properties={"name": name}))
            seen_entities.add(name)

    # Extract named entities via spaCy
    doc = nlp(text[:100_000])  # cap to avoid OOM
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT") and ent.text not in seen_entities:
            entities.append(Entity(name=ent.text, label="Module",
                                   properties={"name": ent.text}))
            seen_entities.add(ent.text)

    # Simple sentence-level relation extraction
    for sent in doc.sents:
        sent_text = sent.text.lower()
        services_in_sent = [e.name for e in entities if e.name.lower() in sent_text]
        if len(services_in_sent) >= 2:
            src, tgt = services_in_sent[0], services_in_sent[1]
            rel_type = "RELATED_TO"
            for verb in DEPENDENCY_VERBS:
                if verb in sent_text:
                    rel_type = "DEPENDS_ON"
                    break
            for verb in EVENT_VERBS:
                if verb in sent_text:
                    rel_type = "PUBLISHES"
                    break
            for verb in CONSUME_VERBS:
                if verb in sent_text:
                    rel_type = "CONSUMES"
                    break
            relations.append(Relation(
                from_name=src, from_label="Service",
                to_name=tgt,   to_label="Service",
                rel_type=rel_type, props={},
            ))

    return entities, relations


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    args = parser.parse_args()
    ents, rels = extract(args.text)
    print(json.dumps({
        "entities": [vars(e) for e in ents],
        "relations": [vars(r) for r in rels],
    }, indent=2))
