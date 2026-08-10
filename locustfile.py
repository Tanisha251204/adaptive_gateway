from locust import HttpUser, task, between


class GatewayUser(HttpUser):
    host = "http://localhost:8000"

    # Simulated "think time" between requests, so this doesn't
    # fire unrealistically as fast as physically possible.

    wait_time = between(0.1, 0.5)

    @task(3)
    def call_service1(self):
        self.client.get("/service1/data")

    @task(1)
    def call_service2(self):
        self.client.get("/service2/data")