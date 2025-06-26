// app/static/js/script.js

/**
 * 编码助手
 * 功能：该文件包含了项目的所有前端交互脚本。
 */

document.addEventListener('DOMContentLoaded', function() {

    // --- 功能1：通用功能 ---

    /**
     * 让所有的 "alert" 提示框在5秒后自动平滑地消失。
     */
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            // 使用Bootstrap的JS API来平滑地关闭提示框
            const bootstrapAlert = new bootstrap.Alert(alert);
            bootstrapAlert.close();
        }, 5000);
    });

    // --- 功能2：Pristine.js 前端表单验证 ---

    // 定义一个通用的 Pristine 配置对象，使其样式能完美融入 Bootstrap 5
    const pristineConfig = {
        classTo: 'form-group',      // 将 'has-success/error' 类应用到这个元素上
        errorTextParent: 'form-group', // 将错误信息插入到这个元素内部
        errorTextClass: 'text-danger small mt-1', // 使用 Bootstrap 的红色小字样式
        errorTextTag: 'div',         // 用 div 标签包裹错误信息
    };

    /**
     * 为“编辑个人资料”表单 (#profile-edit-form) 添加验证
     */
    const profileEditForm = document.getElementById('profile-edit-form');
    if (profileEditForm) {
        const pristineProfile = new Pristine(profileEditForm, pristineConfig);
        profileEditForm.addEventListener('submit', function(e) {
            // 在表单提交前进行验证
            const isValid = pristineProfile.validate();
            if (!isValid) {
                e.preventDefault(); // 如果验证失败，阻止表单提交
            }
        });
    }

    /**
     * 为“用户注册”表单 (#register-form) 添加验证
     */
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        const pristineRegister = new Pristine(registerForm, pristineConfig);
        registerForm.addEventListener('submit', function(e) {
            const isValid = pristineRegister.validate();
            if (!isValid) {
                e.preventDefault(); // 如果验证失败，阻止表单提交
            }
        });
    }

    // --- 功能3：注册页面的动态字段显示 ---

    /**
     * 根据选择的角色，动态显示或隐藏“所属店铺”字段。
     */
    const roleSelect = document.getElementById('role');
    const storeIdField = document.getElementById('store-id-field');

    if (roleSelect && storeIdField) {

        function toggleStoreFieldVisibility() {
            const selectedRole = roleSelect.value;
            // 定义需要选择店铺的角色值 (必须与后端 RoleType 枚举的 .value 一致)
            const storeRequiredRoles = ['employee', 'branch_manager'];
            const storeIdSelect = storeIdField.querySelector('select'); // 获取店铺的select元素

            if (storeRequiredRoles.includes(selectedRole)) {
                storeIdField.style.display = 'block'; // 显示字段
                storeIdSelect.required = true;        // 同时将其设为必填项 (配合Pristine)
            } else {
                storeIdField.style.display = 'none';  // 隐藏字段
                storeIdSelect.required = false;       // 同时取消其必填属性
            }
        }

        // 当角色下拉框的值改变时，调用切换函数
        roleSelect.addEventListener('change', toggleStoreFieldVisibility);
        // 在页面加载时，也立即执行一次，以确保刷新后状态正确
        toggleStoreFieldVisibility();
    }

});
