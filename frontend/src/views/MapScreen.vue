<template>
  <div class="map-screen-container">
    <div class="map-header">
      <h2 class="title">"源网荷储"地理态势全景监控大屏</h2>
      <div class="time-display">{{ currentTime }}</div>
    </div>
    
    <!-- 地图导航栏 -->
    <div class="map-navigation" v-if="mapDataManager">
      <div class="navigation-content">
        <!-- 面包屑导航 -->
        <div class="breadcrumb">
          <span v-for="(item, index) in breadcrumbItems" :key="item.adcode">
            <span class="breadcrumb-item" @click="navigateToBreadcrumb(item.adcode)">
              {{ item.name }}
            </span>
            <span v-if="index < breadcrumbItems.length - 1" class="separator">></span>
          </span>
        </div>
        
        <!-- 导航控制按钮 -->
        <div class="nav-controls">
          <!-- 返回按钮 -->
          <el-button 
            v-if="mapHistory.length > 0" 
            @click="goBack" 
            size="small" 
            type="primary"
            :disabled="isLoadingMap"
          >
            <el-icon><Back /></el-icon>
            返回
          </el-button>
          
          <!-- 创建模式按钮 -->
          <el-button 
            v-if="currentUserRole === 'admin'"
            @click="toggleCreateMode" 
            size="small" 
            :type="isCreateMode ? 'danger' : 'primary'"
            :disabled="isLoadingMap"
            style="margin-left: 10px;"
          >
            <el-icon><Close v-if="isCreateMode" /></el-icon>
            {{ isCreateMode ? '取消创建' : '创建站点' }}
          </el-button>
          
          <!-- 省份快速选择 -->
          <el-select 
            v-model="selectedProvince" 
            @change="onProvinceChange" 
            size="small" 
            placeholder="快速切换省份"
            :disabled="isLoadingMap"
            style="width: 180px; margin-left: 10px;"
          >
            <el-option 
              v-for="province in availableProvinces" 
              :key="province.adcode"
              :label="province.name" 
              :value="province.adcode"
            />
          </el-select>
          
          <!-- 加载状态提示 -->
          <span v-if="isLoadingMap" class="loading-text">
            <el-icon class="loading-icon"><Loading /></el-icon>
            加载地图中...
          </span>
        </div>
      </div>
    </div>
    
    <div class="map-body">
      <!-- 左侧控制面板 -->
      <div class="panel left-panel">
        <div class="panel-box">
          <h3 class="panel-title">调度总览</h3>
          <div class="stat-grid">
            <div class="stat-item" v-for="(v, k) in globalStats" :key="k">
              <span class="stat-label">{{ v.label }}</span>
              <span class="stat-value" :style="{ color: v.color }">{{ v.value }}</span>
            </div>
          </div>
        </div>
        
        <div class="panel-box" style="margin-top: 20px;">
          <h3 class="panel-title">全网实时功率折线</h3>
          <v-chart class="chart chart-small" :option="globalPowerOption" autoresize />
        </div>
      </div>
      
      <!-- 中央地图区域 -->
      <div class="center-map">
        <v-chart ref="mapChart" class="chart chart-map" :option="mapOption" @click="handleMapClick" autoresize />
      </div>

      <!-- 右侧悬浮弹窗 (点击站点出现) -->
      <transition name="fade">
        <div class="panel right-panel" v-if="selectedStation">
          <div class="panel-box">
            <div style="display: flex; justify-content: space-between; align-items: center">
              <h3 class="panel-title">{{ selectedStation.name }}</h3>
              <el-icon @click="selectedStation = null" style="cursor: pointer; color: #fff"><Close /></el-icon>
            </div>
            <p style="color: #409EFF; font-size: 12px; margin-bottom: 15px;">坐标: [{{ selectedStation.value[0] }}, {{ selectedStation.value[1] }}]</p>
            
            <div class="station-meta" v-if="selectedStation.siteData">
              <p>额定容量: {{ selectedStation.siteData.capacity || 40 }} MWh</p>
              <p>最高功率: {{ selectedStation.siteData.power || 20 }} MW</p>
              <p>健康度 (SOH): {{ selectedStation.siteData.soh ? (selectedStation.siteData.soh * 100).toFixed(1) + '%' : '98.5%' }}</p>
              <p v-if="selectedStation.siteData.address">地址: {{ selectedStation.siteData.address }}</p>
              <p v-if="selectedStation.siteData.status">状态: {{ selectedStation.siteData.status }}</p>
            </div>
            <div class="station-meta" v-else>
              <p>额定容量: 40 MWh</p>
              <p>最高功率: 20 MW</p>
              <p>健康度 (SOH): 98.5%</p>
            </div>

            <h3 class="panel-title" style="margin-top: 20px;">储能日内充放策略</h3>
            <v-chart class="chart chart-small" :option="stationDispatchOption" autoresize />
          </div>
        </div>
      </transition>
    </div>
  </div>

  <!-- 创建站点对话框 -->
  <SiteCreateDialog
    v-model="showCreateDialog"
    :coordinates="selectedCoordinates"
    :adcode="currentAdcode"
    @created="onSiteCreated"
  />
</template>

<script>
// ECharts 基础引入
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { MapChart, ScatterChart, EffectScatterChart, LineChart } from 'echarts/charts'
import { GeoComponent, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import * as echarts from 'echarts/core'

// 地图数据管理
import mapDataManager from '@/utils/mapDataManager'

// API函数
import { getSites } from '@/utils/api'

// 组件
import SiteCreateDialog from '@/components/SiteCreateDialog.vue'

// Element Plus 图标
import { Back, Loading, Close } from '@element-plus/icons-vue'

use([
  CanvasRenderer, MapChart, ScatterChart, EffectScatterChart, LineChart, 
  GeoComponent, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent
])

export default {
  name: 'MapScreen',
  components: { 
    VChart,
    SiteCreateDialog,
    Back,
    Loading,
    Close
  },
  data() {
    return {
      currentTime: '',
      timer: null,
      selectedStation: null,
      globalStats: {
        total_power: { label: '总负荷', value: '45.2 MW', color: '#F56C6C' },
        total_pv: { label: '光伏出力', value: '30.1 MW', color: '#E6A23C' },
        total_wind: { label: '风电出力', value: '20.0 MW', color: '#409EFF' },
        ess_status: { label: '储能状态', value: '深度充能中', color: '#67C23A' }
      },
      mapOption: {},
      globalPowerOption: {},
      stationDispatchOption: {},
      // 储能站点数据（从后端API动态加载）
      stations: [],
      isLoadingStations: false,
      stationsError: null,
      mapGeoJson: null,
      
      // ====== 新增：站点创建功能 ======
      isCreateMode: false,
      selectedCoordinates: null,
      showCreateDialog: false,
      currentUserRole: 'admin', // 临时硬编码，后续从用户状态获取
      
      // ====== 新增：全国地图导航状态 ======
      // 当前地图状态
      currentMapLevel: 'nation',      // 'nation' | 'province' | 'city'
      currentAdcode: '100000',        // 当前地图adcode
      currentMapName: '中国',         // 当前地图显示名称
      isLoadingMap: false,            // 地图加载状态
      
      // 导航历史（用于返回功能）
      mapHistory: [],                 // [{adcode, name, level, timestamp}]
      
      // 可用省份列表（从注册表加载）
      availableProvinces: [],
      
      // 选中的省份（用于快速选择器）
      selectedProvince: '',
      
      // 地图数据管理器实例
      mapDataManager: null
    }
  },
  async mounted() {
    this.updateTime()
    this.timer = setInterval(this.updateTime, 1000)
    
    // 初始化地图数据管理器
    await this.initMapDataManager()
    
    // 加载初始地图（全国地图）
    await this.loadInitialMap()
    
    // 加载调度总览数据
    await this.loadGlobalStats()
    
    // 加载实时功率数据
    await this.loadGlobalPowerData()
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    updateTime() {
      const now = new Date()
      this.currentTime = now.toLocaleString('zh-CN', { hour12: false })
    },
    async loadMapData() {
      try {
        // 第一优先级：尝试保底的离线本地地图
        const localData = await import('@/assets/shandong.json');
        this.mapGeoJson = localData.default || localData;
        console.log("成功读取离线山东地图数据");
      } catch (err) {
        // 第二优先级：尝试在线拉取
        console.warn("未能找到本地 shandong.json，尝试在线拉取...", err);
        try {
          const res = await this.$http.get('https://geo.datav.aliyun.com/areas_v3/bound/370000_full.json');
          this.mapGeoJson = res.data;
        } catch (netErr) {
          console.error("在线和离线地图均获取失败", netErr);
        }
      }

      if (this.mapGeoJson) {
        echarts.registerMap('山东', this.mapGeoJson)
      }
    },
    initMapOption() {
      // 获取当前地图信息
      const mapInfo = this.mapDataManager ? this.mapDataManager.getMapInfo(this.currentAdcode) : null
      
      // 动态标题
      const titleText = mapInfo 
        ? `${this.currentMapName} - 各园区微网站点实时分布`
        : '各园区微网站点实时分布'
      
      // 动态地图配置
      const geoConfig = {
        map: this.currentMapName,
        roam: true,
        zoom: mapInfo?.zoom || 1.1,
        center: mapInfo?.center,
        label: {
          show: this.currentMapLevel === 'nation', // 全国显示省份标签，省级显示城市标签
          color: '#ccc',
          fontSize: 10,
          emphasis: { show: true, color: '#fff' }
        },
        itemStyle: {
          // 深色科技风底图
          areaColor: '#0c1538',
          borderColor: '#1ccaff',
          borderWidth: 1.5,
          shadowColor: 'rgba(28, 202, 255, 0.5)',
          shadowBlur: 15
        },
        emphasis: {
          itemStyle: {
            areaColor: '#2a333d'
          },
          label: {
            show: true,
            color: '#fff'
          }
        }
      }
      
      this.mapOption = {
        title: {
          text: titleText,
          left: 'center',
          textStyle: { color: '#ffffff' }
        },
        tooltip: {
          trigger: 'item',
          formatter: (params) => {
            if (params.seriesType === 'effectScatter') {
              return `<b>${params.name}</b><br/>当前负债率综合评分: ${params.value[2]}`
            }
            // 地图区域tooltip
            return `<b>${params.name}</b><br/>点击查看详情`
          }
        },
        geo: geoConfig,
        series: [
          {
            name: '站点',
            type: 'effectScatter',
            coordinateSystem: 'geo',
            data: this.stations,
            symbolSize: 15,
            showEffectOn: 'render',
            rippleEffect: {
              brushType: 'stroke',
              scale: 4
            },
            label: {
              formatter: '{b}',
              position: 'right',
              show: true,
              color: '#fff',
              fontSize: 12
            },
            itemStyle: {
              color: '#f4e925',
              shadowBlur: 10,
              shadowColor: '#333'
            },
            zlevel: 1
          }
        ]
      }
    },
    initGlobalPowerChart() {
      this.globalPowerOption = {
        grid: { top: 30, bottom: 20, left: 35, right: 10 },
        tooltip: { trigger: 'axis' },
        xAxis: { 
          type: 'category', 
          data: ['00', '04', '08', '12', '16', '20', '24'],
          axisLine: { lineStyle: { color: '#5470c6' } },
          axisLabel: { color: '#a1a1a1' }
        },
        yAxis: { 
          type: 'value',
          splitLine: { lineStyle: { color: '#2a333d', type: 'dashed' } },
          axisLabel: { color: '#a1a1a1' }
        },
        series: [
          {
            name: '总流转功率',
            data: [120, 100, 300, 150, 450, 600, 200],
            type: 'line',
            smooth: true,
            lineStyle: { width: 3, color: '#00f2fe' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0, 242, 254, 0.5)' },
                { offset: 1, color: 'rgba(0, 242, 254, 0.01)' }
              ])
            }
          }
        ]
      }
    },
    handleMapClick(params) {
      if (params.componentType === 'series' && params.seriesType === 'effectScatter') {
        const station = this.stations.find(s => s.name === params.name)
        this.selectedStation = station
        // 点击后更新其对应的折线图
        this.buildStationDispatchChart(station)
      }
    },
    buildStationDispatchChart(station) {
      // 这里的充放电、弃风曲线实际上应该通过 `/api/dispatch/history` 取真实数据
      // 为展示酷炫效果，我们使用了一套模拟的鸭子曲线储能策略数据
      this.stationDispatchOption = {
        grid: { top: 30, bottom: 20, left: 35, right: 10 },
        tooltip: { trigger: 'axis' },
        legend: { data: ['充电', '放电'], textStyle: { color: '#ccc' } },
        xAxis: { 
          type: 'category', 
          data: Array.from({length: 24}, (_, i) => i.toString()),
          axisLine: { lineStyle: { color: '#5470c6' } },
          axisLabel: { color: '#ccc', fontSize: 10 }
        },
        yAxis: { 
          type: 'value',
          splitLine: { lineStyle: { color: '#333' } },
          axisLabel: { color: '#ccc', fontSize: 10 }
        },
        series: [
          {
            name: '充电', // 正午深谷充电
            type: 'bar',
            itemStyle: { color: '#67C23A' },
            data: [0,0,0,0,0,0,0,0,0,0,10,20,20,15,0,0,0,0,0,0,0,0,0,0]
          },
          {
            name: '放电', // 傍晚尖峰放电
            type: 'bar',
            itemStyle: { color: '#F56C6C' },
            data: [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,15,20,15,0,0,0,0]
          }
        ]
      }
    },
    
    // ====== 新增：全国地图导航方法 ======
    
    /**
     * 初始化地图数据管理器
     */
    async initMapDataManager() {
      try {
        // 初始化地图数据管理器
        await mapDataManager.init()
        this.mapDataManager = mapDataManager
        
        // 获取可用省份列表
        this.availableProvinces = mapDataManager.getCoreProvinces()
        console.log('地图管理器初始化成功，可用省份:', this.availableProvinces)
      } catch (error) {
        console.error('初始化地图数据管理器失败:', error)
      }
    },

    /** 生成模拟站点数据 */
    generateMockSites() {
      // 根据当前地图区域生成模拟站点
      const adcode = this.currentAdcode
      const level = this.currentMapLevel
      
      // 模拟站点数据
      const mockSites = [
        {
          id: 1,
          name: '北京储能电站',
          adcode: '110000',
          level: 'province',
          longitude: 116.4074,
          latitude: 39.9042,
          capacity: 100,
          power: 50,
          soh: 0.95,
          status: 'active',
          address: '北京市朝阳区'
        },
        {
          id: 2,
          name: '上海储能中心',
          adcode: '310000',
          level: 'province',
          longitude: 121.4737,
          latitude: 31.2304,
          capacity: 120,
          power: 60,
          soh: 0.98,
          status: 'active',
          address: '上海市浦东新区'
        },
        {
          id: 3,
          name: '广东储能基地',
          adcode: '440000',
          level: 'province',
          longitude: 113.2644,
          latitude: 23.1291,
          capacity: 150,
          power: 75,
          soh: 0.92,
          status: 'active',
          address: '广州市天河区'
        },
        {
          id: 4,
          name: '江苏储能站',
          adcode: '320000',
          level: 'province',
          longitude: 118.7969,
          latitude: 32.0603,
          capacity: 80,
          power: 40,
          soh: 0.96,
          status: 'active',
          address: '南京市鼓楼区'
        },
        {
          id: 5,
          name: '浙江储能枢纽',
          adcode: '330000',
          level: 'province',
          longitude: 120.1536,
          latitude: 30.2674,
          capacity: 90,
          power: 45,
          soh: 0.94,
          status: 'active',
          address: '杭州市西湖区'
        }
      ]
      
      // 根据当前地图区域过滤站点
      if (adcode && adcode !== '100000') {
        return mockSites.filter(site => site.adcode === adcode)
      }
      
      // 全国地图显示所有站点
      return mockSites
    },

    /**
     * 加载初始地图（全国地图）
     */
    async loadInitialMap() {
      try {
        this.isLoadingMap = true
        
        // 加载全国地图数据
        const geojson = await this.mapDataManager.loadMap('100000')
        
        // 注册地图到ECharts
        this.mapDataManager.registerMap('100000', geojson, echarts)
        
        // 更新当前状态
        this.currentAdcode = '100000'
        this.currentMapName = '中国'
        this.currentMapLevel = 'nation'
        this.mapHistory = [] // 清空历史
        
        // 初始化地图选项
        this.initMapOption()
        
        // 加载站点数据
        await this.loadStations()
        
        console.log('全国地图加载完成')
      } catch (error) {
        console.error('加载初始地图失败:', error)
        // 尝试加载山东省作为回退
        await this.loadMapData()
      } finally {
        this.isLoadingMap = false
      }
    },
    
    /**
     * 导航到指定地图
     */
    async navigateToMap(adcode) {
      if (this.isLoadingMap) return
      
      try {
        this.isLoadingMap = true
        
        // 获取地图信息
        const mapInfo = this.mapDataManager.getMapInfo(adcode)
        if (!mapInfo) {
          console.error(`未找到地图信息: ${adcode}`)
          return
        }
        
        // 将当前地图添加到历史记录
        if (this.currentAdcode !== adcode) {
          this.mapHistory.push({
            adcode: this.currentAdcode,
            name: this.currentMapName,
            level: this.currentMapLevel,
            timestamp: Date.now()
          })
        }
        
        // 加载新地图数据
        const geojson = await this.mapDataManager.loadMap(adcode)
        
        // 注册地图到ECharts
        this.mapDataManager.registerMap(adcode, geojson, echarts)
        
        // 更新当前状态
        this.currentAdcode = adcode
        this.currentMapName = mapInfo.name
        this.currentMapLevel = mapInfo.level
        
        // 更新地图选项
        this.initMapOption()
        
        // 加载站点数据
        await this.loadStations()
        
        console.log(`导航到地图: ${mapInfo.name} (${adcode})`)
      } catch (error) {
        console.error(`导航到地图 ${adcode} 失败:`, error)
        // 回退到上一级
        if (this.mapHistory.length > 0) {
          const prev = this.mapHistory.pop()
          await this.navigateToMap(prev.adcode)
        }
      } finally {
        this.isLoadingMap = false
      }
    },
    
    /**
     * 返回上一级地图
     */
    async goBack() {
      if (this.mapHistory.length === 0) return
      
      const prev = this.mapHistory.pop()
      await this.navigateToMap(prev.adcode)
    },
    
    /**
     * 处理地图点击事件（扩展）
     */
    handleMapClick(params) {
      // 创建模式：点击地图获取坐标
      if (this.isCreateMode && params.componentType === 'geo') {
        // 转换像素坐标为经纬度
        const chart = this.$refs.mapChart.chart
        if (chart) {
          try {
            const pointInPixel = [params.event.offsetX, params.event.offsetY]
            // 使用 ECharts 5 的正确方法转换坐标
            const coords = chart.convertFromPixel({ geoIndex: 0 }, pointInPixel)
            if (coords && coords.length === 2) {
              this.selectedCoordinates = coords
              this.showCreateDialog = true
              console.log('选择坐标:', coords)
              return
            }
          } catch (error) {
            console.warn('坐标转换失败:', error)
          }
        }
        // 如果转换失败，使用地图中心坐标作为估算
        const mapInfo = this.mapDataManager.getMapInfo(this.currentAdcode)
        if (mapInfo && mapInfo.center) {
          this.selectedCoordinates = mapInfo.center
          this.showCreateDialog = true
        }
        return
      }
      
      // 现有功能：点击站点显示详情
      if (params.componentType === 'series' && params.seriesType === 'effectScatter') {
        const station = this.stations.find(s => s.name === params.name)
        this.selectedStation = station
        // 点击后更新其对应的折线图
        this.buildStationDispatchChart(station)
        return
      }
      
      // 新增功能：点击地图区域进行下钻
      if (params.componentType === 'geo') {
        const regionName = params.name
        
        // 尝试获取adcode
        let targetAdcode = this.mapDataManager.getAdcodeByName(regionName)
        
        // 如果没有找到，可能是省份或城市名称，尝试通过当前地图的子级查找
        if (!targetAdcode && this.mapDataManager.canDrillDown(this.currentAdcode)) {
          const childMaps = this.mapDataManager.getChildMaps(this.currentAdcode)
          const childMap = childMaps.find(child => child.name === regionName)
          if (childMap) {
            targetAdcode = childMap.adcode
          }
        }
        
        if (targetAdcode && this.mapDataManager.canDrillDown(targetAdcode)) {
          this.navigateToMap(targetAdcode)
        }
      }
    },
    
    /**
     * 处理省份选择器变化
     */
    onProvinceChange(adcode) {
      if (adcode) {
        this.navigateToMap(adcode)
        this.selectedProvince = ''
      }
    },
    
    /**
     * 导航到面包屑项
     */
    navigateToBreadcrumb(adcode) {
      // 从历史记录中找到该adcode的位置
      const index = this.mapHistory.findIndex(item => item.adcode === adcode)
      if (index !== -1) {
        // 截断历史记录到该位置
        this.mapHistory = this.mapHistory.slice(0, index)
      }
      this.navigateToMap(adcode)
    },
    
    /**
     * 获取面包屑导航项
     */
    get breadcrumbItems() {
      const items = []
      
      // 添加根节点（全国）
      items.push({ adcode: '100000', name: '中国', level: 'nation' })
      
      // 添加历史记录中的项
      if (this.mapHistory && Array.isArray(this.mapHistory)) {
        this.mapHistory.forEach(item => {
          items.push(item)
        })
      }
      
      // 添加当前项
      if (this.currentAdcode !== '100000') {
        items.push({ 
          adcode: this.currentAdcode, 
          name: this.currentMapName, 
          level: this.currentMapLevel 
        })
      }
      
      return items
    },
    
    /**
     * 切换创建模式
     */
    toggleCreateMode() {
      this.isCreateMode = !this.isCreateMode
      if (this.isCreateMode) {
        this.$message.info('创建模式已开启，请在地图上点击选择位置')
      } else {
        this.selectedCoordinates = null
        this.$message.info('创建模式已关闭')
      }
    },
    
    /**
     * 处理站点创建完成
     */
    onSiteCreated(site) {
      console.log('站点创建成功:', site)
      this.$message.success(`站点 "${site.name}" 创建成功`)
      // 重新加载站点数据
      this.loadStations()
      // 自动切换到普通模式
      this.isCreateMode = false
    },
    
    /**
     * 加载储能站点数据
     */
    async loadStations() {
      if (this.isLoadingStations) return
      
      try {
        this.isLoadingStations = true
        this.stationsError = null
        
        // 根据当前地图层级决定查询参数
        const params = {
          adcode: this.currentAdcode,
          level: this.currentMapLevel,
          status: 'active'
        }
        
        const result = await getSites(params.adcode, params.level, params.status)
        
        if (result.success) {
          // 检查是否有数据
          if (result.data && result.data.length > 0) {
            // 转换API数据为地图需要的格式
            this.stations = result.data.map(site => ({
              name: site.name,
              value: [site.longitude, site.latitude, site.capacity || 50], // 使用容量作为权重
              siteData: site // 保留完整数据用于详情显示
            }))
            console.log(`加载了 ${this.stations.length} 个储能站点`)
          } else {
            // API返回空数据，使用模拟数据
            console.log('API返回空站点数据，使用模拟数据进行展示')
            const mockSites = this.generateMockSites()
            this.stations = mockSites.map(site => ({
              name: site.name,
              value: [site.longitude, site.latitude, site.capacity || 50], // 使用容量作为权重
              siteData: site // 保留完整数据用于详情显示
            }))
          }
          
          // 更新地图显示站点
          if (this.$refs.mapChart) {
            this.initMapOption()
          }
        } else {
          this.stationsError = result.message
          console.error('加载站点数据失败:', result.message)
        }
      } catch (error) {
        this.stationsError = error.message
        console.error('加载站点数据异常:', error)
        
        // 模拟数据：当API不可用时显示示例站点
        console.log('使用模拟站点数据进行展示')
        const mockSites = this.generateMockSites()
        this.stations = mockSites.map(site => ({
          name: site.name,
          value: [site.longitude, site.latitude, site.capacity || 50],
          siteData: site
        }))
        
        // 更新地图显示
        if (this.$refs.mapChart) {
          this.initMapOption()
        }
      } finally {
        this.isLoadingStations = false
      }
    },
    
    /**
     * 加载调度总览数据
     */
    async loadGlobalStats() {
      try {
        // 尝试从后端获取统计数据
        const result = await this.$http.get('/api/data/latest')
        
        if (result.data && result.data.code === 200 && result.data.data && result.data.data.length > 0) {
          const latestData = result.data.data[result.data.data.length - 1]
          
          this.globalStats = {
            total_power: { label: '总负荷', value: `${latestData.load.toFixed(1)} MW`, color: '#F56C6C' },
            total_pv: { label: '光伏出力', value: `${latestData.pv_power.toFixed(1)} MW`, color: '#E6A23C' },
            total_wind: { label: '风电出力', value: `${latestData.wind_power.toFixed(1)} MW`, color: '#409EFF' },
            ess_status: { label: '储能状态', value: '深度充能中', color: '#67C23A' }
          }
          console.log('加载调度总览数据成功:', this.globalStats)
        } else {
          // 使用模拟数据
          console.log('API返回空数据，使用模拟调度总览数据')
          this.globalStats = {
            total_power: { label: '总负荷', value: '45.2 MW', color: '#F56C6C' },
            total_pv: { label: '光伏出力', value: '30.1 MW', color: '#E6A23C' },
            total_wind: { label: '风电出力', value: '20.0 MW', color: '#409EFF' },
            ess_status: { label: '储能状态', value: '深度充能中', color: '#67C23A' }
          }
        }
      } catch (error) {
        console.error('加载调度总览数据失败:', error)
        // 使用模拟数据
        this.globalStats = {
          total_power: { label: '总负荷', value: '45.2 MW', color: '#F56C6C' },
          total_pv: { label: '光伏出力', value: '30.1 MW', color: '#E6A23C' },
          total_wind: { label: '风电出力', value: '20.0 MW', color: '#409EFF' },
          ess_status: { label: '储能状态', value: '深度充能中', color: '#67C23A' }
        }
      }
    },
    
    /**
     * 加载全网实时功率数据
     */
    async loadGlobalPowerData() {
      try {
        // 尝试从后端获取实时功率数据
        const result = await this.$http.get('/api/data/latest', { params: { limit: 24 } })
        
        if (result.data && result.data.code === 200 && result.data.data && result.data.data.length > 0) {
          const powerData = result.data.data
          const hours = powerData.map(item => {
            const date = new Date(item.timestamp)
            return date.getHours().toString().padStart(2, '0')
          })
          const values = powerData.map(item => (item.wind_power + item.pv_power).toFixed(1))
          
          this.globalPowerOption = {
            grid: { top: 30, bottom: 20, left: 35, right: 10 },
            tooltip: { trigger: 'axis' },
            xAxis: { 
              type: 'category', 
              data: hours,
              axisLine: { lineStyle: { color: '#5470c6' } },
              axisLabel: { color: '#a1a1a1' }
            },
            yAxis: { 
              type: 'value',
              splitLine: { lineStyle: { color: '#2a333d', type: 'dashed' } },
              axisLabel: { color: '#a1a1a1' }
            },
            series: [
              {
                name: '总流转功率',
                data: values,
                type: 'line',
                smooth: true,
                lineStyle: { width: 3, color: '#00f2fe' },
                areaStyle: {
                  color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(0, 242, 254, 0.5)' },
                    { offset: 1, color: 'rgba(0, 242, 254, 0.01)' }
                  ])
                }
              }
            ]
          }
          console.log('加载实时功率数据成功:', this.globalPowerOption)
        } else {
          // 使用模拟数据
          console.log('API返回空数据，使用模拟实时功率数据')
          this.initGlobalPowerChart()
        }
      } catch (error) {
        console.error('加载实时功率数据失败:', error)
        // 使用模拟数据
        this.initGlobalPowerChart()
      }
    },
    
    /**
     * 兼容性方法：保留原有的loadMapData用于回退
     */
    async loadMapData() {
      try {
        // 第一优先级：尝试保底的离线本地地图
        const localData = await import('@/assets/shandong.json');
        this.mapGeoJson = localData.default || localData;
        console.log("成功读取离线山东地图数据");
      } catch (err) {
        // 第二优先级：尝试在线拉取
        console.warn("未能找到本地 shandong.json，尝试在线拉取...", err);
        try {
          const res = await this.$http.get('https://geo.datav.aliyun.com/areas_v3/bound/370000_full.json');
          this.mapGeoJson = res.data;
        } catch (netErr) {
          console.error("在线和离线地图均获取失败", netErr);
        }
      }

      if (this.mapGeoJson) {
        echarts.registerMap('山东', this.mapGeoJson)
        // 更新当前状态为山东省
        this.currentAdcode = '370000'
        this.currentMapName = '山东省'
        this.currentMapLevel = 'province'
        this.initMapOption()
      }
    }
  }
}
</script>

<style scoped>
/* 整个大屏的背景色设计 */
.map-screen-container {
  width: 100%;
  height: calc(100vh - 60px); /* 减去顶部Header的高度 */
  background: radial-gradient(circle at center, #0B1021 0%, #030409 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: absolute;
  top: 60px;
  left: 200px;
  right: 0;
  bottom: 0;
  width: auto;
  z-index: 10;
}

/* 侧边栏折叠时的响应式补充，为了简单起见，可以强迫地图全屏覆盖或者通过动态 class 控制，此处用固定 left 作为基础示例 */

.map-header {
  height: 60px;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><line x1="0" y1="100%" x2="100%" y2="100%" stroke="rgba(0, 191, 255, 0.4)" stroke-width="2"/></svg>') no-repeat;
  background-size: 100% 100%;
}

.map-header .title {
  font-size: 24px;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(0, 191, 255, 0.8);
  font-weight: bold;
}

.map-header .time-display {
  position: absolute;
  right: 20px;
  font-family: monospace;
  font-size: 16px;
  color: #00f2fe;
}

.map-body {
  flex: 1;
  display: flex;
  position: relative;
  padding: 20px;
  gap: 20px;
}

.panel {
  width: 320px;
  display: flex;
  flex-direction: column;
  z-index: 2;
  pointer-events: none; /* 让鼠标穿透点击底图 */
}

/* 面板内部需要恢复指针事件 */
.panel-box {
  pointer-events: auto; 
  background: rgba(13, 23, 67, 0.7);
  border: 1px solid rgba(0, 191, 255, 0.3);
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.5) inset;
  padding: 15px;
  border-radius: 8px;
  backdrop-filter: blur(10px);
}

.right-panel {
  position: absolute;
  right: 20px;
  top: 20px;
}

.panel-title {
  margin: 0 0 15px 0;
  font-size: 18px;
  border-left: 4px solid #00f2fe;
  padding-left: 10px;
}

.center-map {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 1;
}

.chart-map {
  width: 100%;
  height: 100%;
}

.chart-small {
  width: 100%;
  height: 220px;
}

.stat-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stat-item {
  width: calc(50% - 5px);
  background: rgba(255, 255, 255, 0.05);
  padding: 10px;
  border-radius: 4px;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #ccc;
  margin-bottom: 5px;
}

.stat-value {
  display: block;
  font-size: 18px;
  font-weight: bold;
}

.station-meta p {
  color: #eee;
  margin: 8px 0;
  font-size: 14px;
}

/* 简单的过渡动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.5s;
}
 .fade-enter-from, .fade-leave-to {
   opacity: 0;
 }

/* ====== 地图导航栏样式 ====== */
.map-navigation {
  background: rgba(13, 23, 67, 0.8);
  border-bottom: 1px solid rgba(0, 191, 255, 0.3);
  padding: 10px 20px;
  backdrop-filter: blur(10px);
}

.navigation-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 14px;
}

.breadcrumb-item {
  color: #00f2fe;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.breadcrumb-item:hover {
  background: rgba(0, 242, 254, 0.1);
  text-decoration: underline;
}

.separator {
  color: #666;
  margin: 0 4px;
}

.nav-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #00f2fe;
  font-size: 12px;
  margin-left: 10px;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式调整 */
@media (max-width: 768px) {
  .navigation-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .nav-controls {
    width: 100%;
    justify-content: space-between;
  }
}

</style>
