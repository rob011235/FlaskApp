INTERCEPT = -119.061877
COEF_HOLIDAY = -29.096613   # if day is holiday or not
COEF_HOUR = 8.626766	    # hour (0 to 23)
COEF_SEASON_1 = 3.523756    # 1: spring
COEF_SEASON_2 = -3.808865   # 2: summer
COEF_SEASON_3 = -42.697445  # 3: fall
COEF_SEASON_4 = 42.982554   # 4: winter
COEF_TEMP = 425.523181      # normalized temp in Celsius -8 to +39


def calc_bike_rentals(holiday, season, temp):
    MEAN_SEASON_1 = MEAN_SEASON_2 = MEAN_SEASON_3 = MEAN_SEASON_4 = 0
    if season == 1:
        MEAN_SEASON_1 = 1
    elif season == 2:
        MEAN_SEASON_2 = 1
    elif season == 3:
        MEAN_SEASON_3 = 1
    elif season == 4:
        MEAN_SEASON_4 = 1
    rental_counts = INTERCEPT + (holiday * COEF_HOLIDAY) \
    + (9 * COEF_HOUR) \
    + (MEAN_SEASON_1 * COEF_SEASON_1)  + (MEAN_SEASON_2 * COEF_SEASON_2) \
    + (MEAN_SEASON_3 * COEF_SEASON_3)  + (MEAN_SEASON_4 * COEF_SEASON_4) \
    + (temp * COEF_TEMP)
    if rental_counts < 0:
        rental_counts = 0
    return int(rental_counts)

if __name__ == "__main__":
    holiday = input("Is it a holiday? (1 for yes, 0 for no): ") == 1
    season = int(input("Enter the season (1: spring, 2: summer, 3: fall, 4: winter): "))
    temp = float(input("Enter the normalized temperature in Celsius (-8 to +39): "))
    rentals = calc_bike_rentals(holiday, season, temp)
    print(f"Estimated bike rentals: {rentals}")
