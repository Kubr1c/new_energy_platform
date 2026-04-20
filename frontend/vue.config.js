const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  lintOnSave: false,
  devServer: {
    port: 8081,
    client: {
      overlay: {
        errors: true,
        warnings: false,
        runtimeErrors: (error) => {
          // Ignore noisy browser ResizeObserver loop errors in dev overlay.
          if (!error || !error.message) return true
          return !error.message.includes('ResizeObserver loop')
        }
      }
    }
  }
})