import logging
import os
from pathlib import Path

from aiohttp import web
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

from ragtools import attach_rag_tools
from rtmt import RTMiddleTier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voicerag")

async def create_app():
    if not os.environ.get("RUNNING_IN_PRODUCTION"):
        logger.info("Running in development mode, loading from .env file")
        load_dotenv()
    llm_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    llm_deployment = os.environ.get("AZURE_OPENAI_REALTIME_DEPLOYMENT")
    llm_key = os.environ.get("AZURE_OPENAI_API_KEY")
    search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    search_index = os.environ.get("AZURE_SEARCH_INDEX")
    search_key = os.environ.get("AZURE_SEARCH_API_KEY")

    credential = None
    if not llm_key or not search_key:
        if tenant_id := os.environ.get("AZURE_TENANT_ID"):
            logger.info("Using AzureDeveloperCliCredential with tenant_id %s", tenant_id)
            credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
        else:
            logger.info("Using DefaultAzureCredential")
            credential = DefaultAzureCredential()
    llm_credential = AzureKeyCredential(llm_key) if llm_key else credential
    search_credential = AzureKeyCredential(search_key) if search_key else credential
    
    app = web.Application()

    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, llm_credential)
    # rtmt.system_message = "You are a helpful assistant expert in answering queries about the Company 'LemonMint Soutions'. Your name is SARAH! As an Expert CSR Only answer questions about your company LemonMint Solutions based on information you searched in the documents, accessible with the 'search' tool. " + \
    #                       "The user is listening to answers with audio, so it's *super* important that answers are as short as possible, a couple of sentences sentences if at all possible. " + \
    #                       "Never read file names or source names or keys out loud. " + \
    #                       "Always use the following step-by-step instructions to respond: \n" + \
    #                       "1. Always use the 'search' tool to check the knowledge base before answering a question. \n" + \
    #                       "2. Always use the 'report_grounding' tool to report the source of information from the knowledge base. \n" + \
    #                       "3. Use the 'current_date' tool if the user asks for today's date. \n" + \
    #                       "4. Produce an answer that's as short as possible. If the answer isn't in the knowledge base, politely say you don't know. \n" + \
    #                       "5. Before you say bye and end the call, politely ask the user if they would like to schedule an online call to know more about your services. If they say yes, then tell them you're sending them an email with the calendly link that they can use to setup a meeting. Send an email to the user using 'send_email' tool. The users email is 'waqasobeidy@outlook.com'. The calendly link is 'https://calendly.com/waqasobeidy/30min'. If the email was sent successfuly then inform the user. if there was an error, tell the user you'll try again shortly. "
    rtmt.system_message = (
        "You are SARAH, an expert customer service assistant for LemonMint Solutions. "
        "Your primary responsibility is to answer questions specifically related to LemonMint Solutions. You must use information from the company knowledge base, accessed via the 'search' tool, to provide accurate responses. "
        "The user is listening to your responses, so it's crucial to make them *extremely* concise, ideally no longer than two sentences. "
        "It is important that you do not read out any file names, source names, or keys from your knowledge base searches. "
        "Please follow these detailed step-by-step instructions to respond effectively: "
        "\n1. **Always use the 'search' tool**: Before answering any question, use the 'search' tool to verify information from the knowledge base. This ensures that the information provided is accurate and up-to-date. Never guess or provide information not explicitly available in the knowledge base. "
        "\n2. **Report the information source**: After retrieving information, use the 'report_grounding' tool to indicate the source of the information you are providing. This ensures transparency and helps maintain credibility, but do not mention this source directly to the user verbally. "
        "\n3. **Provide the current date if asked**: If the user requests today's date, use the 'current_date' tool to provide the most accurate information. "
        "\n4. **Keep responses brief and to the point**: All responses should be as short and simple as possible, ideally just one or two sentences. If the information isn't available in the knowledge base, politely let the user know that you do not have that information. Use phrases like 'I’m sorry, but I don't have that information right now.' "
        "\n5. **Ask about scheduling a call before ending**: Before ending your interaction, always ask the user if they would like to schedule an online call to learn more about LemonMint Solutions' services. "
        "If the user says yes, tell them that you will send them an email with a Calendly link to set up the meeting. Then, proceed to use the 'send_email' tool to send the meeting invitation to 'waqasobeidy@outlook.com'. The Calendly link/url is 'https://calendly.com/waqasobeidy/30min'. Format it as a hyperlink in the email. "
        "\n6. **Confirm email status**: After attempting to send the email, confirm whether it was sent successfully or if there was an error. Inform the user accordingly: if successful, let them know the email has been sent; if there was an error, tell the user that you will try again shortly."
    )
    attach_rag_tools(rtmt, search_endpoint, search_index, search_credential)

    rtmt.attach_to_app(app, "/realtime")

    current_directory = Path(__file__).parent
    app.add_routes([web.get('/', lambda _: web.FileResponse(current_directory / 'static/index.html'))])
    app.router.add_static('/', path=current_directory / 'static', name='static')
    
    return app

if __name__ == "__main__":
    host = "localhost"
    port = 8765
    web.run_app(create_app(), host=host, port=port)
