import pvlib
import pytz

from .ehtools import *

def calculateTsa(epw_file_path:str, convection_heat_transfer:float, solar_absortance:float, inclination:float, azimuth:float, month:str, year:str):
    """
    Calculate Tsa for a surface based on EPW file 

    Arguments:
    ----------
    file -- path location of EPW file
    ho -- 13.
    solar_absortance -- Solar absortance for the material
    inclination -- Inclination of the surface 90 - Vertical
    azimuth -- 270
    month -- Month of interest
    year -- Year of interest
    """
    
    epw, latitud, longitud, altitud, timezone = readEPW(epw_file_path,year,alias=True,warns=False)
    timezone=pytz.timezone('Etc/GMT'+timezone)
    
    
    dia = '15'
    mes = month
    año = year
    absortancia = solar_absortance
    h = convection_heat_transfer

    # Parámetros de la superficie
    surface_tilt = inclination  # 90 - Vertical
    surface_azimuth = azimuth  # 270

    if surface_tilt == 0:
        LWR = 3.9
    else:
        LWR = 0.

    f1 = f'{año}-{mes}-{dia} 00:00'
    f2 = f'{año}-{mes}-{dia} 23:59'

    dia = pd.date_range(start=f1, end=f2, freq='1s',tz=timezone)
    location = pvlib.location.Location(latitude = latitud, 
                                       longitude=longitud, 
                                       altitude=altitud,
                                       tz=timezone)

    dia = location.get_solarposition(dia)
    del dia['apparent_zenith']
    del dia['apparent_elevation']
    
    sunrise,_ = get_sunrise_sunset_times(dia)
    tTmax,Tmin,Tmax = calculate_tTmaxTminTmax(mes,epw)

    # Calcular la temperatura ambiente y agregarla al DataFrame
    dia = temperature_model(dia, Tmin, Tmax, sunrise, tTmax)
    
    # Agrega Ig, Ib, Id a dia 
    dia = add_IgIbId_Tn(dia,epw,mes,f1,f2,timezone)
    
    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=surface_tilt,
        surface_azimuth=surface_azimuth,
        dni=dia['Ib'],
        ghi=dia['Ig'],
        dhi=dia['Id'],
        solar_zenith=dia['zenith'],
        solar_azimuth=dia['azimuth']
    )
    dia['Is'] = total_irradiance.poa_global
    
    # Agrega Tsa, DeltaTn
    dia['Tsa'] = dia.Ta + dia.Is*absortancia/h - LWR
    DeltaTa= dia.Ta.max() - dia.Ta.min()

    dia['DeltaTn'] = calculate_DtaTn(DeltaTa)
    
    epw_mes = epw.loc[epw.index.month==int(mes)]
    hora_minutos = epw_mes.resample('D').To.idxmax()
    hora = hora_minutos.dt.hour
    minuto = hora_minutos.dt.minute
    tTmax = hora.mean() +  minuto.mean()/60 
    Tmin =  epw_mes.resample('D').To.min().resample('ME').mean().iloc[0]
    Tmax =  epw_mes.resample('D').To.max().resample('ME').mean().iloc[0]

    return dia
    