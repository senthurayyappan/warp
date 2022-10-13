import warp as wp


@wp.kernel
def adam_step_kernel_vec3(
    g: wp.array(dtype=wp.vec3),
    m: wp.array(dtype=wp.vec3),
    v: wp.array(dtype=wp.vec3),
    lr: float,
    beta1: float,
    beta2: float,
    t: float,
    eps: float,
    params: wp.array(dtype=wp.vec3),
):
    i = wp.tid()
    m[i] = beta1 * m[i] + (1.0 - beta1) * g[i]
    v[i] = beta2 * v[i] + (1.0 - beta2) * wp.cw_mul(g[i], g[i])
    mhat = m[i] / (1.0 - wp.pow(beta1, (t + 1.0)))
    vhat = v[i] / (1.0 - wp.pow(beta2, (t + 1.0)))
    sqrt_vhat = wp.vec3(wp.sqrt(vhat[0]),wp.sqrt(vhat[1]),wp.sqrt(vhat[2]))
    eps_vec3 = wp.vec3(eps, eps, eps)
    params[i] = params[i] - lr * wp.cw_div(mhat, (sqrt_vhat + eps_vec3))

@wp.kernel
def adam_step_kernel_float(    
    g: wp.array(dtype=float),
    m: wp.array(dtype=float),
    v: wp.array(dtype=float),
    lr: float,
    beta1: float,
    beta2: float,
    t: float,
    eps: float,
    params: wp.array(dtype=float),
):
    i = wp.tid()
    m[i] = beta1 * m[i] + (1.0 - beta1) * g[i]
    v[i] = beta2 * v[i] + (1.0 - beta2) * g[i] * g[i]
    mhat = m[i] / (1.0 - wp.pow(beta1, (t + 1.0)))
    vhat = v[i] / (1.0 - wp.pow(beta2, (t + 1.0)))
    params[i] = params[i] - lr * mhat / (wp.sqrt(vhat) + eps)

# Designed to mimic 
# https://pytorch.org/docs/stable/generated/torch.optim.Adam.html#torch.optim.Adam
class Adam:
    def __init__(self, params=None, lr=0.001, betas=(0.9, 0.999), eps=1e-08):
        self.set_params(params)
        self.lr = lr
        self.beta1 = betas[0]
        self.beta2 = betas[1]
        self.eps = eps
        self.t = 0

    def set_params(self, params):
        self.params = params
        if(params != None):
            self.m = wp.zeros_like(self.params) #first moment
            self.v = wp.zeros_like(self.params) #second moment

    def reset_internal_state(self):
        self.m.zero_()
        self.v.zero_()
        self.t = 0
    
    def solve(self, grad_func, niters=100):
        self.reset_internal_state()
        for _ in range(niters):
            self.step(grad_func())

    # Iter should start from 0
    def step(self, grad):
        assert(self.params != None)
        Adam.step_detail(grad, self.m, self.v, self.lr, self.beta1, self.beta2, self.t, self.eps, self.params)
        self.t = self.t + 1
    
    @staticmethod
    def step_detail(g, m, v, lr, beta1, beta2, t, eps, params):
        assert(params.dtype == g.dtype)
        assert(params.dtype == m.dtype)
        assert(params.dtype == v.dtype)
        kernel_inputs = [g, m, v, lr, beta1, beta2, t, eps, params]
        if(params.dtype == wp.types.float32):
            wp.launch(
                kernel=adam_step_kernel_float,
                dim=len(params),
                inputs=kernel_inputs,
            )
        elif(params.dtype == wp.types.vec3):
            wp.launch(
                kernel=adam_step_kernel_vec3,
                dim=len(params),
                inputs=kernel_inputs,
            )
        else:
            raise RuntimeError("Params data type not supported in Adam step kernels.")