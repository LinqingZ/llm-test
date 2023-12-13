from flask import Flask, request, jsonify, render_template
from langchain.llms import OpenAI
from langchain.document_loaders import PyPDFLoader,WebBaseLoader
from dotenv import load_dotenv
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from flask_cors import CORS 
import openai
import os
import chromadb
from langchain.prompts import PromptTemplate
from chromadb.config import Settings
from langchain.retrievers import SVMRetriever
from langchain.retrievers import ContextualCompressionRetriever
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.callbacks import get_openai_callback

app = Flask(__name__)
CORS(app)
load_dotenv()
API_KEY = os.getenv('OPENAI_API_KEY')
@app.route('/query_open_ai', methods=['POST'])
def query_open_ai():
    content_type = request.headers.get('Content-Type')
    prompt = None
    if (content_type =='application/json'):
        json_payload = request.json
        prompt = json_payload['prompt']
    else:
        return 'Content-Type not supported'
    
    llm = ChatOpenAI(temperature=0, model_name='gpt-3.5-turbo', openai_api_key=API_KEY, max_tokens=100)
    formatted_template = f'Answer like a Normal Person: {prompt}'
    response = llm([HumanMessage(content=formatted_template)])
    return {
        'statusCode': 500,
        'body': response.content
    }
#curl -XPOST --header "Content-Type: application/json" -d {\"prompt\":\"What is 2+2?\"}" 127.0.0.1:5000/query_open_ai

try:
    path = os.path.dirname(os.path.abspath(__file__))
    upload_folder = os.path.join(path, "tmp")
    os.makedirs(upload_folder, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_folder
except Exception as e:
    app.logger.info("Error in creating upload folder:")
    app.logger.error("Exception occured: {}".format(e))

@app.route('/process_pdf', methods=['POST', 'GET'])
def process_pdf():

    pdf_file = request.files['file']
    if pdf_file is not None:

        save_path = os.path.join(app.config.get('UPLOAD_FOLDER'), "temp.pdf")
        pdf_file.save(save_path)

        loader = PyPDFLoader(save_path)

        pages = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(pages)
        embeddings = OpenAIEmbeddings()

        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory="./data"
        )
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

        template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. Use two sentences maximum. Keep the answer as concise as possible. Always say "thanks for asking!" at the end of the answer. 
            {context}
            Question: {question}
            Helpful Answer:"""
        QA_CHAIN_PROMPT = PromptTemplate(input_variables=["context", "question"],template=template,)

        memory = ConversationBufferMemory(
            memory_key="chat_history", #chat history is a lsit of messages
            return_messages=True
        )
        
        qa = ConversationalRetrievalChain.from_llm(
            llm,
            retriever=vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 2}),
            memory=memory
        )

        

        question= request.form.get('question')
        with get_openai_callback() as cb:
            result = qa({"question": question})
        print(cb)
        # tokens_info = {
        #     'tokens_used': cb.total_tokens,
        #     'prompt_tokens': cb.prompt_tokens,
        #     'completion_tokens': cb.completion_tokens,
        #     'total_cost_usd': cb.total_cost
        # }
        # print(tokens_info)
        ans = result.get('answer')
        # print(result['answer'])
        # question="How much are they worth?"
        # result = qa({"question": question})
        # print(result['answer'])
        print(ans)
        return jsonify({
            'statusCode': 200,
            'ans': ans
        })
    else:
        # Return an error response if the file is not provided
        return jsonify({'statusCode': 400, 'error': 'PDF file not provided'})


@app.route('/read_pdf', methods=['GET'])
def read_pdf():
    #pdf_path = os.path.join("llm-test", "hninstory.pdf")
    loader = PyPDFLoader("syllabushnin.pdf")

    pages = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
    )
    chunks = text_splitter.split_documents(pages)

    
    embeddings = OpenAIEmbeddings()

    persist_directory = 'docs/chroma/'
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory="./data"
    )
    print("COLLECTION:", vectordb._collection.count())
    # vectordb.persist()
    
    # docs = vectordb.similarity_search(question, k=2)
    # print("Length docs:", len(docs))
    # print("content docs:", docs[0].page_content[:200])
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    # vectordb.persist()
    # def pretty_print_docs(docs):
    #     print(f"\n{'-' * 100}\n".join([f"Document {i+1}:\n\n" + d.page_content for i, d in enumerate(docs)]))
    # llm = OpenAI(temperature=0)
    # compressor = LLMChainExtractor.from_llm(llm)

    # compression_retriever = ContextualCompressionRetriever(
    # base_compressor=compressor,
    # base_retriever=vectordb.as_retriever()
    # )
#___________________________________#
    # question="Who is the professor?"
    # compressed_docs = compression_retriever.get_relevant_documents(question)
    # print(pretty_print_docs(compressed_docs))
    # qa_chain = RetrievalQA.from_chain_type (
    #     llm,
    #     retriever= vectordb.as_retriever(),
    #     return_source_documents=True,
    #     chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
    # )
    # result = qa_chain({"query": question})
    # print(result["result"])
    #_________________#
    memory = ConversationBufferMemory(
        memory_key="chat_history", #chat history is a lsit of messages
        return_messages=True
    )

    template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. Use two sentences maximum. Keep the answer as concise as possible. Always say "thanks for asking!" at the end of the answer. 
        {context}
        Question: {question}
        Helpful Answer:"""
    QA_CHAIN_PROMPT = PromptTemplate(input_variables=["context", "question"],template=template,)
    qa = ConversationalRetrievalChain.from_llm(
        llm,
        retriever=vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 2}),
        memory=memory,
        return_source_documents=True,
        
        condense_question_prompt=dict(prompt = QA_CHAIN_PROMPT)
    )
    # question="How many programming assignments are there?"
    # with get_openai_callback() as cb:
    #     result = qa({"question": question})
    # print(cb)
    # tokens_info = {
    #         'tokens_used': cb.total_tokens,
    #         'prompt_tokens': cb.prompt_tokens,
    #         'completion_tokens': cb.completion_tokens,
    #         'total_cost_usd': cb.total_cost
    #     }
    # print("token1", tokens_info)
    # print(result['answer'])
    # print(result)
    # question="How much are they worth?"
    # with get_openai_callback() as cb3:
    #     result = qa({"question": question})
    # print("cb3", cb3)
    # tokens_info = {
    #         'tokens_used': cb.total_tokens,
    #         'prompt_tokens': cb.prompt_tokens,
    #         'completion_tokens': cb.completion_tokens,
    #         'total_cost_usd': cb.total_cost
    #     }
    # print("token2", tokens_info)
    # print(result['answer'])
    # print(result)
    return {
        'statusCode': 500,
    
    }


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)


