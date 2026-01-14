from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
import json
import yaml
import os
from datetime import datetime
import tempfile

from .models import IncidentInput, PostmortemOutput, JiraTicket
from .generator import PostmortemGenerator
from .templates import PostmortemTemplate
from .pdf_converter import PDFConverter
from .jira_integration import JiraIntegration


app = FastAPI(title="Incident Postmortem Generator", version="1.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize components
generator = PostmortemGenerator()
template_engine = PostmortemTemplate()
pdf_converter = PDFConverter()


class GenerateRequest(BaseModel):
    incident_data: dict
    format: str = "markdown"  # markdown, pdf, both
    jira_config: Optional[dict] = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate", response_class=HTMLResponse)
async def generate_postmortem(
    request: Request,
    incident_data: str = Form(...),
    output_format: str = Form("markdown"),
    jira_url: Optional[str] = Form(None),
    jira_username: Optional[str] = Form(None),
    jira_token: Optional[str] = Form(None),
    jira_project: Optional[str] = Form(None)
):
    try:
        # Parse incident data (try JSON first, then YAML)
        try:
            incident_dict = json.loads(incident_data)
        except json.JSONDecodeError:
            incident_dict = yaml.safe_load(incident_data)
        
        # Convert to IncidentInput model
        incident = IncidentInput(**incident_dict)
        
        # Generate postmortem
        postmortem = generator.generate_postmortem(incident)
        
        # Generate output based on format
        results = {}
        
        if output_format in ["markdown", "both"]:
            markdown_content = template_engine.render_markdown(postmortem)
            results["markdown"] = markdown_content
        
        if output_format in ["pdf", "both"]:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                pdf_path = tmp_file.name
            
            success = pdf_converter.convert_to_pdf(postmortem, pdf_path)
            if success:
                results["pdf_path"] = pdf_path
            else:
                results["pdf_error"] = "Failed to generate PDF"
        
        # Generate Jira tickets if configured
        if jira_url and jira_username and jira_token and jira_project:
            try:
                jira_integration = JiraIntegration(jira_url, jira_username, jira_token)
                tickets = jira_integration.create_action_item_tickets(
                    postmortem.action_items, jira_project, postmortem
                )
                results["jira_tickets"] = tickets
            except Exception as e:
                results["jira_error"] = str(e)
        
        return templates.TemplateResponse("result.html", {
            "request": request,
            "postmortem": postmortem,
            "results": results,
            "output_format": output_format
        })
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/download/{file_type}")
async def download_file(file_type: str, file_path: str):
    if file_type == "pdf" and os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/pdf", filename="postmortem.pdf")
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/generate")
async def api_generate(request: GenerateRequest):
    try:
        # Convert to IncidentInput model
        incident = IncidentInput(**request.incident_data)
        
        # Generate postmortem
        postmortem = generator.generate_postmortem(incident)
        
        # Generate output based on format
        results = {"postmortem": postmortem.dict()}
        
        if request.format in ["markdown", "both"]:
            markdown_content = template_engine.render_markdown(postmortem)
            results["markdown"] = markdown_content
        
        if request.format in ["pdf", "both"]:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                pdf_path = tmp_file.name
            
            success = pdf_converter.convert_to_pdf(postmortem, pdf_path)
            if success:
                results["pdf_path"] = pdf_path
            else:
                results["pdf_error"] = "Failed to generate PDF"
        
        # Generate Jira tickets if configured
        if request.jira_config:
            try:
                jira_integration = JiraIntegration(
                    request.jira_config["url"],
                    request.jira_config["username"], 
                    request.jira_config["token"]
                )
                tickets = jira_integration.create_action_item_tickets(
                    postmortem.action_items, 
                    request.jira_config["project_key"], 
                    postmortem
                )
                results["jira_tickets"] = tickets
            except Exception as e:
                results["jira_error"] = str(e)
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
