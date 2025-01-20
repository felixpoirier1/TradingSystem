from Gateway import TWSGateway
from Engine import Engine

def main():
    app = TWSGateway()
    engine = Engine(app)
    engine.launch()

if __name__ == "__main__":
    main()
    