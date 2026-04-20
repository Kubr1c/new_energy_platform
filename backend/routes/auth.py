"""
认证相关API路由
提供用户注册、登录、个人信息管理等功能
"""

from flask import Blueprint, request, jsonify, current_app
from models.database import db, User
import jwt
import datetime
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def _get_secret_key():
    """从 Flask app config 统一读取 SECRET_KEY"""
    return current_app.config['SECRET_KEY']


def token_required(f):
    """
    JWT令牌验证装饰器
    
    功能：验证请求中的JWT令牌，确保用户已登录
    参数：f - 被装饰的函数
    返回：验证通过后执行原函数，否则返回错误信息
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'code': 401, 'message': '令牌格式错误'}), 401
        
        if not token:
            return jsonify({'code': 401, 'message': '缺少访问令牌'}), 401
        
        try:
            data = jwt.decode(token, _get_secret_key(), algorithms=["HS256"])
            current_user = db.session.get(User, data['user_id'])
            if not current_user:
                return jsonify({'code': 401, 'message': '用户不存在'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': '无效令牌'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """
    用户注册接口
    
    请求参数：
        username: str - 用户名
        password: str - 密码
        role: str - 角色（可选，默认为operator）
    
    返回值：
        code: 200 - 注册成功
        message: str - 操作结果消息
        data: dict - 用户信息
            id: int - 用户ID
            username: str - 用户名
            role: str - 用户角色
    
    错误处理：
        400 - 缺少必填字段或用户名已存在
        500 - 注册失败
    """
    try:
        data = request.json
        
        # 验证必需字段
        required_fields = ['username', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'code': 400, 'message': f'缺少{field}字段'})
        
        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'code': 400, 'message': '用户名已存在'})
        
        # 创建新用户（禁止通过注册接口自选 admin 角色）
        requested_role = data.get('role', 'operator')
        if requested_role not in ('operator', 'viewer'):
            requested_role = 'operator'
        
        new_user = User(
            username=data['username'],
            role=requested_role
        )
        new_user.set_password(data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'code': 200, 
            'message': '注册成功',
            'data': {
                'id': new_user.id,
                'username': new_user.username,
                'role': new_user.role
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'注册失败: {str(e)}'})

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """
    用户登录接口
    
    请求参数：
        username: str - 用户名
        password: str - 密码
    
    返回值：
        code: 200 - 登录成功
        message: str - 操作结果消息
        data: dict - 登录信息
            token: str - JWT令牌
            user: dict - 用户信息
                id: int - 用户ID
                username: str - 用户名
                role: str - 用户角色
    
    错误处理：
        400 - 缺少用户名或密码
        401 - 用户名或密码错误
        500 - 登录失败
    """
    try:
        data = request.json
        
        # 验证必需字段
        if not data.get('username') or not data.get('password'):
            return jsonify({'code': 400, 'message': '缺少用户名或密码'})
        
        # 查找用户
        user = User.query.filter_by(username=data['username']).first()
        if not user:
            return jsonify({'code': 401, 'message': '用户名或密码错误'})
        
        # 验证密码（支持自动从明文迁移到哈希）
        if not user.check_password(data['password']):
            return jsonify({'code': 401, 'message': '用户名或密码错误'})
        
        # 生成JWT令牌（使用 Flask app config 中的 SECRET_KEY）
        token = jwt.encode({
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, _get_secret_key(), algorithm="HS256")
        
        return jsonify({
            'code': 200, 
            'message': '登录成功',
            'data': {
                'token': token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role
                }
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'登录失败: {str(e)}'})

@auth_bp.route('/api/auth/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """
    获取用户信息接口
    
    功能：获取当前登录用户的详细信息
    
    返回值：
        code: 200 - 获取成功
        data: dict - 用户信息
            id: int - 用户ID
            username: str - 用户名
            role: str - 用户角色
            created_at: str - 创建时间
    """
    return jsonify({
        'code': 200,
        'data': {
            'id': current_user.id,
            'username': current_user.username,
            'role': current_user.role,
            'created_at': current_user.created_at.isoformat()
        }
    })

@auth_bp.route('/api/auth/change_password', methods=['POST'])
@token_required
def change_password(current_user):
    """
    修改密码接口
    
    请求参数：
        old_password: str - 旧密码
        new_password: str - 新密码
    
    返回值：
        code: 200 - 修改成功
        message: str - 操作结果消息
    
    错误处理：
        400 - 缺少必填字段或旧密码错误
        500 - 密码修改失败
    """
    try:
        data = request.json
        
        # 验证必需字段
        required_fields = ['old_password', 'new_password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'code': 400, 'message': f'缺少{field}字段'})
        
        # 验证旧密码
        if not current_user.check_password(data['old_password']):
            return jsonify({'code': 400, 'message': '旧密码错误'})
        
        # 更新密码（使用哈希存储）
        current_user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '密码修改成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'密码修改失败: {str(e)}'})

@auth_bp.route('/api/auth/users', methods=['GET'])
@token_required
def get_users(current_user):
    """
    获取用户列表接口（仅管理员）
    
    功能：获取所有用户的详细信息
    权限：仅管理员可访问
    
    返回值：
        code: 200 - 获取成功
        data: list - 用户列表
            每个元素为用户信息字典
                id: int - 用户ID
                username: str - 用户名
                role: str - 用户角色
                created_at: str - 创建时间
    
    错误处理：
        403 - 权限不足
        500 - 查询失败
    """
    if current_user.role != 'admin':
        return jsonify({'code': 403, 'message': '权限不足'})
    
    try:
        users = User.query.all()
        result = []
        for user in users:
            result.append({
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'created_at': user.created_at.isoformat()
            })
        
        return jsonify({'code': 200, 'data': result})
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败: {str(e)}'})

@auth_bp.route('/api/auth/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    """
    更新用户信息接口（仅管理员）
    
    功能：更新指定用户的角色信息
    权限：仅管理员可访问
    
    请求参数：
        role: str - 新角色（admin/operator/viewer）
    
    返回值：
        code: 200 - 更新成功
        message: str - 操作结果消息
        data: dict - 用户信息
            id: int - 用户ID
            username: str - 用户名
            role: str - 用户角色
    
    错误处理：
        403 - 权限不足
        404 - 用户不存在
        400 - 无效的角色
        500 - 更新失败
    """
    if current_user.role != 'admin':
        return jsonify({'code': 403, 'message': '权限不足'})
    
    try:
        data = request.json
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify({'code': 404, 'message': '用户不存在'})
        
        # 更新角色
        if 'role' in data:
            if data['role'] in ['admin', 'operator', 'viewer']:
                user.role = data['role']
            else:
                return jsonify({'code': 400, 'message': '无效的角色'})
        
        db.session.commit()
        
        return jsonify({
            'code': 200, 
            'message': '用户信息更新成功',
            'data': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'更新失败: {str(e)}'})

@auth_bp.route('/api/auth/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    """
    删除用户接口（仅管理员）
    
    功能：删除指定用户
    权限：仅管理员可访问
    
    返回值：
        code: 200 - 删除成功
        message: str - 操作结果消息
    
    错误处理：
        403 - 权限不足
        404 - 用户不存在
        400 - 不能删除当前登录用户
        500 - 删除失败
    """
    if current_user.role != 'admin':
        return jsonify({'code': 403, 'message': '权限不足'})
    
    try:
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify({'code': 404, 'message': '用户不存在'})
        
        if user.id == current_user.id:
            return jsonify({'code': 400, 'message': '不能删除当前登录用户'})
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '用户删除成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'删除失败: {str(e)}'})

@auth_bp.route('/api/auth/users/<int:user_id>/reset_password', methods=['POST'])
@token_required
def reset_user_password(current_user, user_id):
    """
    重置用户密码接口（仅管理员）
    
    功能：重置指定用户的密码
    权限：仅管理员可访问
    
    请求参数：
        new_password: str - 新密码
    
    返回值：
        code: 200 - 重置成功
        message: str - 操作结果消息
    
    错误处理：
        403 - 权限不足
        404 - 用户不存在
        400 - 缺少新密码字段
        500 - 密码重置失败
    """
    if current_user.role != 'admin':
        return jsonify({'code': 403, 'message': '权限不足'})
    
    try:
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify({'code': 404, 'message': '用户不存在'})
        
        data = request.json
        if not data or not data.get('new_password'):
            return jsonify({'code': 400, 'message': '缺少新密码字段'})
        
        # 更新密码（使用哈希存储）
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'code': 200, 'message': '密码重置成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'密码重置失败: {str(e)}'})
