// app/static/js/script.js

/**
 * 编码助手
 * 功能：该文件包含了项目的所有前端交互脚本。
 */

document.addEventListener('DOMContentLoaded', function() {
    /**
     * 功能1：让所有的 "alert" 提示框在3秒后自动消失。
     * (此功能为您已有的代码，我们予以保留)
     */
    const alerts = document.querySelectorAll('.alert-dismissible');
    if (alerts) {
        alerts.forEach(function(alert) {
            setTimeout(function() {
                // 使用Bootstrap的JS API来平滑地关闭提示框，体验更好
                const bootstrapAlert = new bootstrap.Alert(alert);
                bootstrapAlert.close();
            }, 5000); // 5 秒后关闭
        });
    }


    /**
     * 【核心新增功能】: 使用 Pristine.js 来处理员工档案表单验证
     */
    // 1. 找到我们在HTML中定义好ID的表单
    const staffForm = document.getElementById('staff-edit-form');

    // 2. 确认页面上存在这个表单，才执行后续操作
    if (staffForm) {

        // 3. 定义Pristine的配置对象，让它的样式完美融入Bootstrap 5
        const pristineConfig = {
            // Pristine应该将 'has-success' 或 'has-error' 这些状态类，添加到哪个元素的class上
            classTo: 'form-group',
            // Pristine应该将错误提示文本，插入到哪个元素的内部
            errorTextParent: 'form-group',
            // Pristine生成的错误提示文本，应该是什么样式
            errorTextClass: 'text-danger', // 使用Bootstrap的红色文字样式
            // Pristine生成的错误提示文本，应该用什么HTML标签包裹
            errorTextTag: 'div',
        };

        // 4. 创建Pristine的实例！
        //    我们把表单元素和配置传给它
        const pristine = new Pristine(staffForm, pristineConfig);

        // 5. 监听表单的提交事件 (实现“提交时拦截”)
        staffForm.addEventListener('submit', function(event) {
            // 调用pristine.validate()来检查整个表单，它会返回一个布尔值
            const isValid = pristine.validate();

            // 如果验证失败
            if (!isValid) {
                // 就调用 event.preventDefault()，强制阻止表单的默认提交行为
                event.preventDefault();
            }
        });
    }
});