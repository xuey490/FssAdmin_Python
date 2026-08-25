export const relationsType: { name: string; value: string }[] = [
  { name: '一对一[hasOne]', value: 'hasOne' },
  { name: '一对多[hasMany]', value: 'hasMany' },
  { name: '一对一（反向)[belongsTo]', value: 'belongsTo' },
  { name: '多对多[belongsToMany]', value: 'belongsToMany' }
]

export const queryType: { label: string; value: string }[] = [
  { label: '=', value: 'eq' },
  { label: '!=', value: 'neq' },
  { label: '>', value: 'gt' },
  { label: '>=', value: 'gte' },
  { label: '<', value: 'lt' },
  { label: '<=', value: 'lte' },
  { label: 'LIKE', value: 'like' },
  { label: 'IN', value: 'in' },
  { label: 'NOT IN', value: 'notin' },
  { label: 'BETWEEN', value: 'between' }
]

// 页面控件
export const viewComponent: { label: string; value: string }[] = [
  { label: '输入框', value: 'input' },
  { label: '文本域', value: 'textarea' },
  { label: '下拉框', value: 'select' },
  { label: '单选框', value: 'radio' },
  { label: '复选框', value: 'checkbox' },
  { label: '日期控件', value: 'datetime' },
  { label: '图片上传', value: 'imageUpload' },
  { label: '文件上传', value: 'fileUpload' },
  { label: '富文本编辑器', value: 'editor' }
]
