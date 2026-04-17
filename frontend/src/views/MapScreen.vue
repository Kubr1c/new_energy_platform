<template>
  <div class="map-screen-container">
    <div class="map-header">
      <h2 class="title">“源网荷储”地理态势全景监控大屏</h2>
      <div class="time-display">{{ currentTime }}</div>
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
            
            <div class="station-meta">
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
</template>

<script>
// ECharts 基础引入
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { MapChart, ScatterChart, EffectScatterChart, LineChart } from 'echarts/charts'
import { GeoComponent, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import * as echarts from 'echarts/core'

use([
  CanvasRenderer, MapChart, ScatterChart, EffectScatterChart, LineChart, 
  GeoComponent, TitleComponent, TooltipComponent, LegendComponent, GridComponent, VisualMapComponent
])

export default {
  name: 'MapScreen',
  components: { VChart },
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
      // 模拟山东省的几个储能站点
      stations: [
        { name: '济南高芯储能微网', value: [117.00, 36.65, 80] }, // 经度, 纬度, SOC/重要性权重
        { name: '青岛临港储能微网', value: [120.33, 36.07, 45] },
        { name: '烟台数字园区储能站', value: [121.39, 37.52, 90] }
      ],
      mapGeoJson: null
    }
  },
  async mounted() {
    this.updateTime()
    this.timer = setInterval(this.updateTime, 1000)
    
    // 加载地图JSON
    await this.loadMapData()
    this.initMapOption()
    this.initGlobalPowerChart()
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
      this.mapOption = {
        title: {
          text: '各园区微网站点实时分布',
          left: 'center',
          textStyle: { color: '#ffffff' }
        },
        tooltip: {
          trigger: 'item',
          formatter: function (params) {
            if (params.seriesType === 'effectScatter') {
              return `<b>${params.name}</b><br/>当前负债率综合评分: ${params.value[2]}`
            }
            return params.name
          }
        },
        geo: {
          map: '山东',
          roam: true,
          zoom: 1.1,
          label: {
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
            }
          }
        },
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

</style>
