import redis

def test():
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    redis_client.set("name", "LigaAcLabs")
    data = redis_client.get("name")
    print(data.decode("utf-8"))


if __name__ == "__main__":
    test()