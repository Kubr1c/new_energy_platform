/**
 * 地图数据管理工具类
 * 支持多级缓存策略：内存 → localStorage → 网络 → 几何回退
 * 动态地图注册管理，支持全国→省份→城市三级导航
 */

import axios from 'axios'

class MapDataManager {
  constructor() {
    // 内存缓存
    this.memoryCache = new Map()
    
    // 已注册地图集合（避免重复注册）
    this.registeredMaps = new Set()
    
    // 地图注册表信息
    this.mapRegistry = null
    
    // 加载状态跟踪
    this.loadingStates = new Map()
    
    // 默认配置
    this.config = {
      localStorageKey: 'map-data-cache',
      cacheDurationDays: 30,
      maxMemoryCacheSize: 20,
      retryCount: 3,
      retryDelay: 1000
    }
  }

  /**
   * 初始化地图管理器（加载注册表）
   */
  async init() {
    try {
      const registry = await import('@/assets/map-data/map-registry.json')
      this.mapRegistry = registry.default || registry
      console.log('地图注册表加载成功，包含', this.mapRegistry.maps.length, '个地图')
      return this.mapRegistry
    } catch (error) {
      console.error('加载地图注册表失败:', error)
      // 创建默认注册表
      this.mapRegistry = {
        maps: [
          { adcode: '100000', name: '中国', level: 'nation', center: [104.195, 35.861], zoom: 1.2 }
        ],
        dataSources: {
          primary: 'https://raw.githubusercontent.com/lyhmyd1211/GeoMapData_CN/master/geojson/{adcode}.json',
          backup: 'https://geo.datav.aliyun.com/areas_v3/bound/{adcode}_full.json',
          fallback: 'geometry'
        }
      }
      return this.mapRegistry
    }
  }

  /**
   * 获取地图信息
   */
  getMapInfo(adcode) {
    if (!this.mapRegistry) return null
    return this.mapRegistry.maps.find(map => map.adcode === adcode) || null
  }

  /**
   * 获取父级地图adcode
   */
  getParentAdcode(adcode) {
    const mapInfo = this.getMapInfo(adcode)
    return mapInfo ? mapInfo.parent : null
  }

  /**
   * 获取子级地图列表
   */
  getChildMaps(adcode) {
    if (!this.mapRegistry) return []
    const mapInfo = this.getMapInfo(adcode)
    if (!mapInfo || !mapInfo.children) return []
    
    return mapInfo.children
      .map(childAdcode => this.getMapInfo(childAdcode))
      .filter(info => info !== null)
  }

  /**
   * 检查是否可下钻（有子级地图）
   */
  canDrillDown(adcode) {
    const mapInfo = this.getMapInfo(adcode)
    return mapInfo && (mapInfo.hasCityData || (mapInfo.children && mapInfo.children.length > 0))
  }

  /**
   * 根据名称获取adcode
   */
  getAdcodeByName(name) {
    if (!this.mapRegistry) return null
    const map = this.mapRegistry.maps.find(m => m.name === name)
    return map ? map.adcode : null
  }

  /**
   * 加载地图数据（四级缓存策略）
   */
  async loadMap(adcode) {
    // 检查是否正在加载
    if (this.loadingStates.has(adcode)) {
      return this.loadingStates.get(adcode)
    }

    const loadPromise = this._loadMapWithCache(adcode)
    this.loadingStates.set(adcode, loadPromise)
    
    try {
      const result = await loadPromise
      return result
    } finally {
      this.loadingStates.delete(adcode)
    }
  }

  /**
   * 四级缓存加载实现
   */
  async _loadMapWithCache(adcode) {
    // 1. 内存缓存
    if (this.memoryCache.has(adcode)) {
      console.log(`地图 ${adcode} 从内存缓存加载`)
      return this.memoryCache.get(adcode)
    }

    // 2. localStorage缓存
    const cachedData = this._getLocalStorageCache(adcode)
    if (cachedData) {
      console.log(`地图 ${adcode} 从localStorage缓存加载`)
      this.memoryCache.set(adcode, cachedData)
      this._manageMemoryCache()
      return cachedData
    }

    // 3. 网络下载
    try {
      const networkData = await this._downloadMap(adcode)
      console.log(`地图 ${adcode} 从网络下载成功`)
      
      // 存储到缓存
      this.memoryCache.set(adcode, networkData)
      this._setLocalStorageCache(adcode, networkData)
      this._manageMemoryCache()
      
      return networkData
    } catch (error) {
      console.error(`地图 ${adcode} 网络下载失败:`, error)
      
      // 4. 几何回退（生成简单边界）
      const fallbackData = this._createFallbackGeometry(adcode)
      console.log(`地图 ${adcode} 使用几何回退`)
      
      this.memoryCache.set(adcode, fallbackData)
      this._manageMemoryCache()
      
      return fallbackData
    }
  }

  /**
   * 从localStorage获取缓存
   */
  _getLocalStorageCache(adcode) {
    try {
      const cacheKey = `${this.config.localStorageKey}-${adcode}`
      const cached = localStorage.getItem(cacheKey)
      if (!cached) return null
      
      const cacheData = JSON.parse(cached)
      
      // 检查过期时间
      const now = Date.now()
      if (cacheData.expiresAt && now > cacheData.expiresAt) {
        localStorage.removeItem(cacheKey)
        return null
      }
      
      return cacheData.data
    } catch (error) {
      console.error('读取localStorage缓存失败:', error)
      return null
    }
  }

  /**
   * 设置localStorage缓存
   */
  _setLocalStorageCache(adcode, data) {
    try {
      const cacheKey = `${this.config.localStorageKey}-${adcode}`
      const cacheData = {
        data,
        cachedAt: Date.now(),
        expiresAt: Date.now() + (this.config.cacheDurationDays * 24 * 60 * 60 * 1000)
      }
      localStorage.setItem(cacheKey, JSON.stringify(cacheData))
    } catch (error) {
      console.error('写入localStorage缓存失败:', error)
    }
  }

  /**
   * 管理内存缓存大小
   */
  _manageMemoryCache() {
    if (this.memoryCache.size > this.config.maxMemoryCacheSize) {
      // 删除最久未使用的项（简单实现：删除第一个）
      const firstKey = this.memoryCache.keys().next().value
      this.memoryCache.delete(firstKey)
    }
  }

  /**
   * 从网络下载地图数据
   */
  async _downloadMap(adcode, retryCount = this.config.retryCount) {
    const mapInfo = this.getMapInfo(adcode)
    
    // 如果有本地文件，优先使用
    if (mapInfo && mapInfo.localFile) {
      try {
        const localData = await import(`@/assets/map-data/${mapInfo.localFile}`)
        return localData.default || localData
      } catch (error) {
        console.warn(`本地文件 ${mapInfo.localFile} 加载失败:`, error)
      }
    }
    
    // 尝试主要数据源
    const sources = [
      this.mapRegistry?.dataSources?.primary,
      this.mapRegistry?.dataSources?.backup
    ].filter(Boolean)
    
    for (let attempt = 0; attempt < retryCount; attempt++) {
      for (const sourceTemplate of sources) {
        try {
          const url = sourceTemplate.replace('{adcode}', adcode)
          console.log(`尝试下载地图 ${adcode}，URL: ${url}`)
          
          const response = await axios.get(url, { timeout: 10000 })
          
          if (response.data && response.data.type === 'FeatureCollection') {
            return response.data
          } else {
            throw new Error('无效的GeoJSON格式')
          }
        } catch (error) {
          console.warn(`数据源 ${sourceTemplate} 尝试失败:`, error.message)
          if (attempt === retryCount - 1 && sourceTemplate === sources[sources.length - 1]) {
            throw error // 所有尝试都失败
          }
        }
      }
      
      // 重试前等待
      if (attempt < retryCount - 1) {
        await new Promise(resolve => setTimeout(resolve, this.config.retryDelay))
      }
    }
    
    throw new Error(`所有数据源都失败，adcode: ${adcode}`)
  }

  /**
   * 创建几何回退数据（简单矩形边界）
   */
  _createFallbackGeometry(adcode) {
    const mapInfo = this.getMapInfo(adcode)
    let bbox = null
    
    if (mapInfo && mapInfo.center) {
      // 基于中心点创建简单边界框
      const [lng, lat] = mapInfo.center
      bbox = [
        [lng - 2, lat - 1], // 西南
        [lng + 2, lat - 1], // 东南
        [lng + 2, lat + 1], // 东北
        [lng - 2, lat + 1], // 西北
        [lng - 2, lat - 1]  // 闭合
      ]
    } else {
      // 默认中国边界
      bbox = [
        [73.5, 18.0], // 西南
        [135.0, 18.0], // 东南
        [135.0, 53.5], // 东北
        [73.5, 53.5], // 西北
        [73.5, 18.0]  // 闭合
      ]
    }
    
    return {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {
            adcode,
            name: mapInfo?.name || adcode,
            center: mapInfo?.center || [104.195, 35.861]
          },
          geometry: {
            type: 'Polygon',
            coordinates: [bbox]
          }
        }
      ]
    }
  }

  /**
   * 注册地图到ECharts
   */
  registerMap(adcode, geojson, echartsInstance) {
    const mapInfo = this.getMapInfo(adcode)
    const mapName = mapInfo ? mapInfo.name : adcode
    
    if (this.registeredMaps.has(mapName)) {
      console.log(`地图 ${mapName} 已注册，跳过`)
      return
    }
    
    try {
      echartsInstance.registerMap(mapName, geojson)
      this.registeredMaps.add(mapName)
      console.log(`地图 ${mapName} 注册成功`)
    } catch (error) {
      console.error(`注册地图 ${mapName} 失败:`, error)
    }
  }

  /**
   * 检查地图是否已注册
   */
  isMapRegistered(mapName) {
    return this.registeredMaps.has(mapName)
  }

  /**
   * 获取核心省份列表
   */
  getCoreProvinces() {
    if (!this.mapRegistry) return []
    
    const coreAdcodes = this.mapRegistry.coreProvinces || []
    return coreAdcodes
      .map(adcode => this.getMapInfo(adcode))
      .filter(info => info !== null)
  }

  /**
   * 清理缓存
   */
  clearCache(adcode = null) {
    if (adcode) {
      // 清理指定地图缓存
      this.memoryCache.delete(adcode)
      
      try {
        const cacheKey = `${this.config.localStorageKey}-${adcode}`
        localStorage.removeItem(cacheKey)
      } catch (error) {
        console.error('清理localStorage缓存失败:', error)
      }
    } else {
      // 清理所有缓存
      this.memoryCache.clear()
      
      try {
        const keysToRemove = []
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i)
          if (key.startsWith(this.config.localStorageKey)) {
            keysToRemove.push(key)
          }
        }
        
        keysToRemove.forEach(key => localStorage.removeItem(key))
      } catch (error) {
        console.error('清理所有localStorage缓存失败:', error)
      }
    }
    
    console.log(`缓存清理完成 ${adcode ? `(${adcode})` : '(全部)'}`)
  }
}

// 创建单例实例
const mapDataManager = new MapDataManager()

export default mapDataManager