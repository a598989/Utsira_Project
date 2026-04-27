from API.frost_api import FrostAPI

def main():
    frost = FrostAPI()
    df = frost.get_wind_data()

    print(df.head())

if __name__ == "__main__":
    main()