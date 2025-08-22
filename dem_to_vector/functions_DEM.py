from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateTransform, QgsFeatureRequest, QgsVectorFileWriter, QgsProcessingFeedback, QgsCoordinateReferenceSystem, QgsRasterLayer, QgsApplication, QgsRectangle, QgsGeometry, QgsFeature
from qgis.gui import QgsMapCanvas
from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant, QFileInfo
import processing
import os
import math

def path_exp(expFolder):
    if not os.path.exists(expFolder):  
        os.makedirs(expFolder)  
        print(f'Создана папка {expFolder}')  
    else:  
        print(f'Папка {expFolder} была ранее создана')  
        
def pixels_to_points(input_raster, chek): #Пиксели в точки
    #if chek:
    #    input_raster = input_raster.source()
    params = {'INPUT_RASTER':input_raster,
              'RASTER_BAND':1,
              'FIELD_NAME':'Z',
              'OUTPUT':'memory:pixels_to_points'
              }
    feedback = QgsProcessingFeedback()
    alg_name = 'native:pixelstopoints'
    result = processing.run(alg_name, params, feedback=feedback)['OUTPUT']
    QgsProject.instance().addMapLayer(result,chek)
    return result
        
def set_z_from_raster(input_raster, input_vector,chek):#Взять значение Z с растра
    params = {'INPUT':input_vector,
              'RASTER':input_raster,
              'OUTPUT':'memory:point_with_Z'
              }
    feedback = QgsProcessingFeedback()
    alg_name = 'native:setzfromraster'
    result = processing.run(alg_name, params, feedback=feedback)['OUTPUT']
    QgsProject.instance().addMapLayer(result,chek)
    return result
        
def export_dxf(input_vector,expFolder):
    QgsVectorFileWriter.writeAsVectorFormat(input_vector, expFolder, 'utf-8', input_vector.crs(), 'DXF', skipAttributeCreation=True)     
    #QgsVectorFileWriter.writeAsVectorFormat(input_vector, 
    #    expFolder + '\\' + input_vector.name() + ".dxf", 'utf-8', input_vector.crs(), 'DXF', skipAttributeCreation=True)  
    #print(f'Файл {input_vector.name()} сохранен в папку {expFolder}')
        
#Обрезка растра
def clip_raster(input_raster, input_vector,flag,chek):
    if flag != 2:
        #Обрезка по маске
        alg_name = 'gdal:cliprasterbymasklayer'
        params = {'INPUT': input_raster,
                  'MASK': input_vector,
                  'NODATA': 255.0,
                  'OPTIONS': 'COMPRESS=LZW',
                  'OUTPUT':'TEMPORARY_OUTPUT'
                  }
        
    else:
        #Обрезка по охвату
        ext = input_vector.extent() #ввод координат
        vector_crs = input_vector.crs()
        #if flag == 2:   
        #    #Обрезка по охвату
        #    ext = input_vector.extent() #ввод координат
        #    vector_crs = input_vector.crs()
        #else:
        #    # Получаем текущий холст карты
        #    canvas = iface.mapCanvas()
        #    # Получаем экстент (границы) видимой области
        #    ext = canvas.extent()
        #    vector_crs = canvas.mapSettings().destinationCrs()

        # Преобразуем экстент, если CRS разные
        if type(input_raster) is str:
            raster_crs = QgsRasterLayer(input_raster).crs()
        else:
            raster_crs = input_raster.crs()
 
        if raster_crs != vector_crs:
            transform = QgsCoordinateTransform(vector_crs, raster_crs, QgsProject.instance())
            ext = transform.transformBoundingBox(ext) 

        # Форматируем PROJWIN
        projwin = f"{ext.xMinimum()},{ext.xMaximum()},{ext.yMinimum()},{ext.yMaximum()}"
        alg_name = 'gdal:cliprasterbyextent'
        params = {'INPUT': input_raster,
                  'PROJWIN': projwin,
                  'NODATA': 255.0,
                  'OPTIONS': 'COMPRESS=LZW',
                  'OUTPUT':'TEMPORARY_OUTPUT'
                  }
    output_raster = processing.run(alg_name, params)['OUTPUT']
    if chek:
        output_raster = raster_import_to_proj(output_raster)
        output_raster = QgsProject.instance().mapLayersByName(output_raster.name())[0]
        output_raster.setName('clip_raster')
        #result = output_raster.source()
    return output_raster
    
#Обрезка по маске
def clip_raster_by_vector(input_raster, input_vector, overwrite=False):
    # if overwrite:
    #     if os.path.isfile(output_raster):
    #         os.remove(output_raster)

    if not os.path.isfile(input_raster):
        print ("File doesn't exists", input_raster)
        return None
    else:
        params = {'INPUT': input_raster,
                  'MASK': input_vector,
                  'OUTPUT':'TEMPORARY_OUTPUT'
                  }

        alg_name = 'gdal:cliprasterbymasklayer'
        output_raster = processing.run(alg_name, params)['OUTPUT']
        if chek:
            output_raster = raster_import_to_proj(output_raster)
            output_raster = QgsProject.instance().mapLayersByName(output_raster.name())[0]
            output_raster.setName('clip_raster')
            #result = output_raster.source()
        return output_raster

#Обрезка по координатам
def clip_raster_by_extent(input_raster, input_xy, overwrite=False):
    # if overwrite:
    #     if os.path.isfile(output_raster):
    #         os.remove(output_raster)

    if not os.path.isfile(input_raster):
        print ("File doesn't exists", input_raster)
        return None
    else:
        params = {'INPUT': input_raster,
                  'PROJWIN': input_xy,
                  'NODATA': 255.0,
                  'ALPHA_BAND': False,
                  'OPTIONS': 'COMPRESS=LZW',
                  'DATA_TYPE': 0,  # Byte
                  'OUTPUT':'TEMPORARY_OUTPUT'
                  }

        alg_name = 'gdal:cliprasterbyextent'
        output_raster = processing.run(alg_name, params)['OUTPUT']
        if chek:
            output_raster = raster_import_to_proj(output_raster)
            output_raster = QgsProject.instance().mapLayersByName(output_raster.name())[0]
            output_raster.setName('clip_raster')
            #result = output_raster.source()
        return output_raster
        
#Импорт растра в проект по ссылке
def raster_import_to_proj(fileName): 
    fileInfo = QFileInfo(fileName)
    baseName = fileInfo.baseName()
    input_raster = QgsRasterLayer(fileName, baseName)
    if not input_raster.isValid():
        print ("Layer failed to load!")
    QgsProject.instance().addMapLayer(input_raster)
    return(input_raster)
    # return (r'/'+baseName)
    
# Перепроецирование растра
def warpreproject(input_raster,crs_proj,chek):
    alg_name = "gdal:warpreproject"
    params = {'INPUT':input_raster,
        'TARGET_CRS':crs_proj, # Система координат
        'OUTPUT':'TEMPORARY_OUTPUT'
        }
    output_raster = processing.run(alg_name, params)['OUTPUT'] 
    if chek:
        output_raster = raster_import_to_proj(output_raster)
        output_raster = QgsProject.instance().mapLayersByName(output_raster.name())[0]
        output_raster.setName('warp_raster')
        #result = output_raster.source()
    return output_raster

def ReprojectLayer(input_vector,target_crs,chek):
    alg_name = "native:reprojectlayer"
    params = {'INPUT':input_vector,
        'TARGET_CRS':target_crs, # Система координат
        'OUTPUT':'memory:transform_vector'
        }
    result = processing.run(alg_name, params)['OUTPUT'] 
    QgsProject.instance().addMapLayer(result,chek)
    return result


# Поиск растра по охвату вектора
def serch_raster(input_vector, raster_archive, flag, chek):
    raster_list = []
    if flag == 3:
        # Получаем текущий холст карты
        canvas = iface.mapCanvas()
        # Получаем экстент (границы) видимой области
        ext = canvas.extent()
        crsSrc = canvas.mapSettings().destinationCrs()
    else:
        ext = input_vector.extent()
        crsSrc = input_vector.crs()
    
    crsDest = QgsCoordinateReferenceSystem("EPSG:4326")
    if crsSrc != crsDest:
 #       transformContext = QgsProject.instance().transformContext()
 #       transform = QgsCoordinateTransform(crsSrc, crsDest, transformContext)
 #       ext = transform.transform(ext)
        transform = QgsCoordinateTransform(crsSrc, crsDest, QgsProject.instance())
        ext = transform.transformBoundingBox(ext) 
    x_min = math.floor(ext.xMinimum())
    y_min = math.floor(ext.yMinimum())
    x_max = math.floor(ext.xMaximum())
    y_max = math.floor(ext.yMaximum())
        
    
    while y_max - y_min + 1 > 0:
        x_min = math.floor(ext.xMinimum())
        while x_max - x_min + 1 > 0:
            
            if y_min >= 0:
                ordinate = 'N'
                if x_min >= 0:
                    abscissa = 'E'
                else:
                    abscissa = 'W'
            else:
                ordinate = 'S'
                if x_min >= 0:
                    abscissa = 'E'
                else:
                    abscissa = 'W'
            
            c = '0' # символ  
            n = 3 - len(str(x_min)) # количество раз  
            x_x = c * n + str(x_min)
            c = '0' # символ  
            n = 2 - len(str(y_min)) # количество раз  
            y_y = c * n + str(y_min)
            
            raster_name = f'\{ordinate}{y_y}{abscissa}{x_x}_FABDEM_V1-2.tif'
            input_raster = raster_archive + raster_name
            raster_list.append(input_raster)
            if chek:
                raster_import_to_proj(input_raster) #Импорт растра исходника
            x_min += 1
        y_min += 1
    return(raster_list)
    
# Объеддинение растров из списка путей
def MergeRaster(raster_list, chek):
    alg_name = "gdal:merge"
    params = {'INPUT':raster_list,
            'DATA_TYPE':5,
            'OUTPUT':'TEMPORARY_OUTPUT'
            }
    output_raster = processing.run(alg_name, params)['OUTPUT']
    if chek:
        output_raster = raster_import_to_proj(output_raster)
        output_raster = QgsProject.instance().mapLayersByName(output_raster.name())[0]
        output_raster.setName('merge_raster')
    return output_raster

# создать векторный слой с прямоугольником, соответствующим видимой области карты
def create_extent_rectangle_layer(chek):
    # Получаем текущий экстент карты
    canvas = iface.mapCanvas()
    extent = canvas.extent()
    
    # Создаем временный векторный слой (в памяти)
    layer = QgsVectorLayer("Polygon?crs={}".format(canvas.mapSettings().destinationCrs().authid()), 
                          "Видимая область", "memory")
    
    # Создаем прямоугольник из экстента
    rect = QgsRectangle(extent)
    polygon = QgsGeometry.fromRect(rect)
    
    # Создаем и добавляем объект в слой
    feature = QgsFeature()
    feature.setGeometry(polygon)
    layer.dataProvider().addFeature(feature)
    
    # Обновляем слой и добавляем в проект
    layer.updateExtents()
    QgsProject.instance().addMapLayer(layer,chek)
    
    return layer