// app/static/js/extensionState.js
/**
 * 扩展状态管理（占位文件）
 * 此文件用于防止浏览器扩展相关的加载错误
 */

// 防止重复加载和扩展冲突
if (typeof window.ExtensionState === 'undefined') {
    window.ExtensionState = {
        initialized: true,
        version: '1.0.0',

        // 基础状态管理
        state: {},

        // 获取状态
        getState: function(key) {
            return this.state[key] || null;
        },

        // 设置状态
        setState: function(key, value) {
            this.state[key] = value;
        }
    };
}
