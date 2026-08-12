import APIClient from '@/services/APIClient';

export default class DeviceAuth {
    static async approve(user_code: string): Promise<boolean> {
        const response = await APIClient.post('/users/device-auth/approve', {user_code});
        return response.type !== 'error';
    }
}
