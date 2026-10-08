from datetime import datetime, timezone
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from bson import ObjectId

from config.db import conn


note = APIRouter()
templates = Jinja2Templates(directory="templates")


def format_timestamp(value):
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%b %d, %Y at %I:%M %p UTC")
    return str(value)


def note_sort_timestamp(doc):
    value = doc.get("created_at") or doc["_id"].generation_time
    if not isinstance(value, datetime):
        value = doc["_id"].generation_time
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

@note.get("/", response_class=HTMLResponse)
async def new_note_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@note.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="about.html",
        context={},
    )


@note.get("/collection", response_class=HTMLResponse)
async def read_item(request: Request):
    docs = list(conn.NotesDB.notes.find({}))
    docs.sort(key=note_sort_timestamp, reverse=True)
    new_docs = [
        {
            "id": str(doc["_id"]),
            "title": doc.get("title", doc.get("note", "Untitled note")),
            "desc": doc.get("desc", ""),
            "important": bool(doc.get("important", False)),
            "created_at": format_timestamp(
                doc.get("created_at") or doc["_id"].generation_time
            ),
            "updated_at": format_timestamp(doc.get("updated_at")),
        }
        for doc in docs
    ]

    return templates.TemplateResponse(
        request=request,
        name="collection.html",
        context={"newDocs": new_docs},
    )


@note.post("/", response_class=HTMLResponse)
async def create_note(request: Request):
    form = parse_qs((await request.body()).decode("utf-8"))
    title = form.get("title", [""])[0].strip()
    desc = form.get("desc", [""])[0].strip()
    important = form.get("important", [""])[0] == "true"
    if not title or not desc:
        return RedirectResponse(url="/", status_code=303)
    conn.NotesDB.notes.insert_one(
        {
            "title": title,
            "desc": desc,
            "important": important,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return RedirectResponse(url="/collection", status_code=303)


@note.get("/notes/{note_id}/edit", response_class=HTMLResponse)
async def edit_note_page(request: Request, note_id: str):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    doc = conn.NotesDB.notes.find_one({"_id": ObjectId(note_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return templates.TemplateResponse(
        request=request,
        name="edit_note.html",
        context={
            "note": {
                "id": note_id,
                "title": doc.get("title", doc.get("note", "")),
                "desc": doc.get("desc", ""),
                "important": bool(doc.get("important", False)),
            }
        },
    )


@note.post("/notes/{note_id}/edit")
async def update_note(request: Request, note_id: str):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    form = parse_qs((await request.body()).decode("utf-8"))
    title = form.get("title", [""])[0].strip()
    desc = form.get("desc", [""])[0].strip()
    if not title or not desc:
        return RedirectResponse(url=f"/notes/{note_id}/edit", status_code=303)
    conn.NotesDB.notes.update_one(
        {"_id": ObjectId(note_id)},
        {
            "$set": {
                "title": title,
                "desc": desc,
                "important": form.get("important", [""])[0] == "true",
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    return RedirectResponse(url="/collection", status_code=303)


@note.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: str):
    if not ObjectId.is_valid(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    result = conn.NotesDB.notes.delete_one({"_id": ObjectId(note_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return Response(status_code=204)
