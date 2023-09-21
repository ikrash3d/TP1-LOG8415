from flask import Flask

app = Flask(__name__)


@app.route("/")
def base_route():
    return "Base Route!"


@app.route("/cluster1")
def cluster1_route():
    return "Cluster number 1 is responding now!"


@app.route("/cluster2")
def cluster2_route():
    return "Cluster number 2 is responding now!"


if __name__ == "__main__":
    app.run(debug=True)
