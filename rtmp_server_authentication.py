from fastapi import FastAPI, HTTPException, Request

app = FastAPI()

SECRET_KEY = "4QOtJYZtBNXYZqGt"


@app.post("/authenticate")
async def authenticate(request: Request):
    form_data = await request.form()
    key = form_data.get("key")

    if key == SECRET_KEY:
        return "OK"
    else:
        raise HTTPException(status_code=403, detail="Forbidden")
