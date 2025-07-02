from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/webhook")
async def show_body(request: Request):
    data = await request.json()
    print(data)
    return data


@app.post("/check")
async def check():
    return 'Ok'
