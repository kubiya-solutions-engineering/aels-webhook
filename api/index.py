from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/webhook")
async def show_body(request: Request):
    data = await request.json()
    print(data)
    return data

@app.get("/")
def read_root():
    return {"message": "Look Ma, I'm deployed!"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
