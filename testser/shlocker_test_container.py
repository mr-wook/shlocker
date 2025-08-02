#/bin/env python3

if True:
    from   fastapi import FastAPI
    import uvicorn

app = FastAPI()  # Create the FastAPI "app" instance

@app.get("/")   # Declare a GET endpoint at path "/"
async def read_root():
    return {"message": "hello"}  # FastAPI will serialize this dict to JSON

if __name__ == "__main__":
    uvicorn.run("shlocker_test_container:app", reload=True, host="0.0.0.0", port=9999)
