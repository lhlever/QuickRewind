import React from 'react'

// 全新测试组件 - 创建时间: 2025-11-20 23:59:59
const TestApp = () => {
  // 立即执行的测试代码
  React.useEffect(() => {
    alert('🎉 全新测试组件加载成功！这是新文件！');
    console.log('🎉 TestApp.jsx 已加载');
  }, []);

  return (
    <div style={{
      padding: '50px',
      textAlign: 'center',
      fontSize: '24px',
      backgroundColor: '#4CAF50',
      color: 'white',
      minHeight: '100vh'
    }}>
      <h1>✅ 新测试组件工作正常！</h1>
      <p>如果你能看到这个绿色页面和弹窗，说明构建系统工作正常</p>
      <p>时间戳: 2025-11-20 23:59:59</p>
    </div>
  )
}

export default TestApp
