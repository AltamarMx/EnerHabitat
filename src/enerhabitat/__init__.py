import pvlib
import pytz

from datetime import datetime
from .ehtools import *

La = 2.5
Nx = 20     # Number of elements to discretize
ho = 13     # Outside convection heat transfer
hi = 8.6    # Inside convection heat transfer
dt = 60

@njit
def meanDay(
    epw_file : str,
    day = "15",
    month = "current_month",
    year = "current_year"
    ) -> pd.DataFrame:
    """
    Calculates the ambient temperature per second for the average day based on EPW file data.
    
    Args:
        epw_file (str): Path to the EPW file. 
        day (str, optional): Day of interest. Defaults to 15.
        month (str, optional): Month of interest. Defaults to current month.
        year (str, optional): Year of interest. Defaults to current year.

    Returns:
        DataFrame: Predicted ambient temperature ( Ta ), global ( Ig ), direct ( Ib ) 
        and diffuse irradiance ( Id ) per second for the average day of the specified month and year.
    """
    
    if month == "current_month": month = datetime.now().month
    if year == "current_year": year = datetime.now().year

    f1 = f'{year}-{month}-{day} 00:00'
    f2 = f'{year}-{month}-{day} 23:59'
    
    epw, latitud, longitud, altitud, timezone = readEPW(epw_file,year,alias=True,warns=False)
    timezone=pytz.timezone('Etc/GMT'+f'{(-timezone):+}')
    
    dia_promedio = pd.date_range(start=f1, end=f2, freq='1s',tz=timezone)
    location = pvlib.location.Location(latitude = latitud, 
                                       longitude=longitud, 
                                       altitude=altitud,
                                       tz=timezone)

    dia_promedio = location.get_solarposition(dia_promedio)
    del dia_promedio['apparent_zenith']
    del dia_promedio['apparent_elevation']
    
    sunrise,_ = get_sunrise_sunset_times(dia_promedio)
    tTmax,Tmin,Tmax = calculate_tTmaxTminTmax(month, epw)

    # Calculate ambient temperature y add to the DataFrame
    dia_promedio = add_temperature_model(dia_promedio, Tmin, Tmax, sunrise, tTmax)
    
    # Add Ig, Ib, Id y Tn a dia_promedio 
    dia_promedio = add_IgIbId_Tn(dia_promedio, month, f1, f2, timezone)
    
    # Add DeltaTn
    DeltaTa= dia_promedio.Ta.max() - dia_promedio.Ta.min()
    dia_promedio['DeltaTn'] = calculate_DtaTn(DeltaTa)
    
    return dia_promedio

@njit
def Tsa(
    meanDay_dataframe:pd.DataFrame,
    solar_absortance: float,
    surface_tilt: float,
    surface_azimuth: float,
    ) -> pd.DataFrame: 
    """
    Calculates the sun-air temperature per second for the average day experienced
    by a surface based on a meanDay dataframe.
    
    Args:
        meanDay_dataframe (DataFrame): Data frame containing ambient temperature ( Ta ), global ( Ig ), direct ( Ib ) and diffuse irradiance ( Id ). 
        solar_absortance (float): Solar absortance of the system's external material.
        surface_tilt (float): Surface tilt relative to the ground, 90° == Vertical.
        surface_azimuth (float): Deviation from true north, 0° == North.
    
    Returns:
        DataFrame: Predicted sun-air temperature ( Tsa ) and solar irradiance ( Is )
        per second for the average day.
    """
    
    global ho
    outside_convection_heat_transfer = ho
    
    if surface_tilt == 0:
        LWR = 3.9
    else:
        LWR = 0.
        
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=surface_tilt,
        surface_azimuth=surface_azimuth,
        dni=meanDay_dataframe['Ib'],
        ghi=meanDay_dataframe['Ig'],
        dhi=meanDay_dataframe['Id'],
        solar_zenith=meanDay_dataframe['zenith'],
        solar_azimuth=meanDay_dataframe['azimuth']
    )
    
    # Add Is
    meanDay_dataframe['Is'] = total_irradiance.poa_global
    
    # Add Tsa
    meanDay_dataframe['Tsa'] = meanDay_dataframe.Ta + meanDay_dataframe.Is*solar_absortance/outside_convection_heat_transfer - LWR
       
    return meanDay_dataframe

@njit    
def solveCS(
    constructive_system:list,
    Tsa_dataframe:pd.DataFrame,
    )->pd.DataFrame:
    """
    Solves the constructive system's inside temperature with the TSA simulation dataframe.

    Args:
        constructive_system (list): list of tuples from outside to inside with material and width.
        Tsa_dataframe (DataFrame): Predicted sun-air temperature ( TSA ) per second for the average day DataFrame.
        
    Returns:
        DataFrame: Interior temperature ( Ti ) for the constructive system.
    """
    
    global La 
    global Nx     # Number of elements to discretize
    global ho     # Outside convection heat transfer
    global hi     # Inside convection heat transfer
    global dt  
       
    propiedades = read_materials()
    
    cs = set_construction(propiedades, constructive_system)
    
    k, rhoc, dx = set_k_rhoc(cs, Nx)

    T = np.full(Nx, Tsa_dataframe.Tn.mean())
    Tsa_dataframe['Ti'] = Tsa_dataframe.Tn.mean()
    
    Tsa_dataframe = Tsa_dataframe.iloc[::dt]
    
    C = 1
    while C > 5e-4: 
        Told = T.copy()
        for tiempo, datos in Tsa_dataframe.iterrows():
            a,b,c,d = calculate_coefficients(dt, dx, k, Nx, rhoc, T, datos["Tsa"], ho, datos["Ti"], hi)
            T, Ti = solve_PQ(a, b, c, d, T, Nx, datos['Ti'], hi, La, dt)
            Tsa_dataframe.loc[tiempo,"Ti"] = Ti
        Tnew = T.copy()
        C = abs(Told - Tnew).mean()
        FD   = (Tsa_dataframe.Ti.max() - Tsa_dataframe.Ti.min())/(Tsa_dataframe.Ta.max()-Tsa_dataframe.Ta.min())
        FDsa = (Tsa_dataframe.Ti.max() - Tsa_dataframe.Ti.min())/(Tsa_dataframe.Tsa.max()-Tsa_dataframe.Tsa.min())
    
    return Tsa_dataframe