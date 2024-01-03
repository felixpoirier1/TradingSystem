from Gateway import AlpacaGateway
from Engine import Engine

def main():
    app = AlpacaGateway()
    engine = Engine(app)
    engine.launch()

if __name__ == "__main__":
    main()
    