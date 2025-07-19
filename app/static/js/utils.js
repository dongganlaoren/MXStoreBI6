// app/static/js/utils.js
/**
 * 通用工具函数库
 */

// 防止重复加载
if (typeof window.AppUtils === 'undefined') {
    window.AppUtils = {
        // 工具函数可以在这里添加
        initialized: true,

        // 通用提示函数
        showMessage: function(message, type = 'info') {
            console.log(`[${type.toUpperCase()}]: ${message}`);
        },

        // 表单验证辅助函数
        validateForm: function(formElement) {
            if (!formElement) return false;
            return formElement.checkValidity();
        }
    };
}
