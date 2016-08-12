##############################################################################
#
# Copyright (c) 2016, Mandar Chitre
#
# This file is part of arlpy which is released under Simplified BSD License.
# See file LICENSE or go to http://www.opensource.org/licenses/BSD-3-Clause
# for full license details.
#
##############################################################################

"""Communications toolbox."""

import numpy as _np
import scipy.signal as _sp

from numpy import pi as _pi, sin as _sin, cos as _cos, sqrt as _sqrt
from signal import time as _time

# set up population count table for fast BER computation
_MAX_M = 64
_popcount = _np.empty(_MAX_M, dtype=_np.int)
for _i in range(_MAX_M):
    _popcount[_i] = bin(_i).count('1')

def random_data(size, m=2):
    """Generate random symbols in the range [0, m-1].

    :param size: number of data points (or shape) to produce
    :param m: symbol alphabet size

    >>> import arlpy
    >>> arlpy.comms.random_data(10)
    array([1, 0, 0, 1, 1, 0, 1, 0, 1, 0])
    >>> arlpy.comms.random_data(10, 4)
    array([0, 2, 2, 3, 2, 3, 2, 0, 1, 0])
    >>> arlpy.comms.random_data((2,2))
    array([[0, 1],
           [0, 0]])
    """
    return _np.random.randint(0, m, size)

def gray_code(m):
    """Generate a Gray code map of size m.

    :param m: symbol alphabet size
    :returns: a mapping from integers (indices) to Gray coded integers

    >>> import arlpy
    >>> x = arlpy.comms.gray_code(8)
    >>> x
    array([0, 1, 3, 2, 6, 7, 5, 4])
    >>> x[3]   # 3 => 2
    2
    """
    x = range(m)
    x = map(lambda a: a ^ (a >> 1), x)
    return _np.asarray(x)

def invert_map(x):
    """Generate an inverse map.

    :param x: map, such as that generated by :func:`gray_code`
    :returns: an inverse map y, such that `y[x[j]] = j`

    >>> import arlpy
    >>> x = arlpy.comms.gray_code(8)
    >>> y = arlpy.comms.invert_map(x)
    >>> x[2]
    3
    >>> y[3]
    2
    """
    y = _np.empty_like(x)
    y[x] = _np.arange(len(x))
    return y

def bi2sym(x, m):
    """Convert bits to symbols.

    :param x: bit array
    :param m: symbol alphabet size (must be a power of 2)
    :returns: symbol array

    >>> import arlpy
    >>> arlpy.comms.bi2sym([0, 0, 1, 0, 1, 0, 1, 1, 1], 8)
    array([1, 2, 7])
    """
    n = int(_np.log2(m))
    if 2**n != m:
        raise ValueError('m must be a power of 2')
    x = _np.asarray(x, dtype=_np.int)
    if _np.any(x < 0) or _np.any(x > 1):
        raise ValueError('Invalid data bits')
    nsym = len(x)/n
    x = _np.reshape(x, (nsym, n))
    y = _np.zeros(nsym, dtype=_np.int)
    for i in range(n):
        y <<= 1
        y |= x[:, i]
    return y

def sym2bi(x, m):
    """Convert symbols to bits.

    :param x: symbol array
    :param m: symbol alphabet size (must be a power of 2)
    :returns: bit array

    >>> import arlpy
    >>> arlpy.comms.sym2bi([1, 2, 7], 8)
    array([0, 0, 1, 0, 1, 0, 1, 1, 1])
    """
    n = int(_np.log2(m))
    if 2**n != m:
        raise ValueError('m must be a power of 2')
    x = _np.asarray(x, dtype=_np.int)
    if _np.any(x < 0) or _np.any(x >= m):
        raise ValueError('Invalid data for specified m')
    y = _np.zeros((len(x), n), dtype=_np.int)
    for i in range(n):
        y[:, n-i-1] = (x >> i) & 1
    return _np.ravel(y)

def ook():
    """Generate an on-off keying constellation.

    The constellation represents the baseband values for bits 0 and 1
    respectively. The constellation is scaled for unit average
    energy per bit, assuming the bits are randomly distributed.

    >>> import arlpy
    >>> arlpy.comms.ook()
    array([0, 1.414])
    """
    return _np.array([0, _sqrt(2)], dtype=_np.float)

def pam(m=2, gray=True, centered=True):
    """Generate a PAM constellation with m signal points.

    The constellation represents the baseband values for symbols 0 through m-1
    respectively. The constellation is scaled for unit average energy per
    symbol, assuming the symbols are randomly distributed.

    :param m: symbol alphabet size
    :param gray: True to use Gray coding, False otherwise
    :param centered: True to center constellation around 0, False otherwise

    >>> import arlpy
    >>> arlpy.comms.pam()
    array([-1, 1])
    >>> arlpy.comms.pam(m=4, gray=False, centered=False)
    array([0, 0.535, 1.069, 1.604])
    """
    if gray and 2**int(_np.log2(m)) != m:
        raise ValueError('m must be a power of 2 if Gray coding is desired')
    x = _np.arange(m, dtype=_np.float)
    if centered:
        x -= _np.mean(x)
    x /= _sqrt(_np.mean(x**2))
    if gray:
        x = x[invert_map(gray_code(m))]
    return x

def psk(m=2, phase0=None, gray=True):
    """Generate a PSK constellation with m signal points.

    The constellation represents the baseband values for symbols 0 through m-1
    respectively. The constellation is scaled for unit average energy per
    symbol, assuming the symbols are randomly distributed.

    :param m: symbol alphabet size
    :param phase0: phase of the 0 symbol (`None` => pi/4 for QPSK, 0 otherwise)
    :param gray: True to use Gray coding, False otherwise

    >>> import arlpy
    >>> arlpy.comms.psk()
    array([1+0j, -1+0j])
    >>> arlpy.comms.psk(4)
    array([0.707+0.707j, -0.707+0.707j, 0.707-0.707j, -0.707-0.707j])
    >>> arlpy.comms.iqplot(arlpy.comms.psk(4))
    """
    if phase0 is None:
        phase0 = _pi/4 if m == 4 else 0
    x = _np.round(_np.exp(1j*(2*_pi/m*_np.arange(m)+phase0)), decimals=8)
    if gray:
        x = x[invert_map(gray_code(m))]
    return x

def qam(m=16, gray=True):
    """Generate a QAM constellation with m signal points.

    The constellation represents the baseband values for symbols 0 through m-1
    respectively. The constellation is scaled for unit average energy per
    symbol, assuming the symbols are randomly distributed.

    :param m: symbol alphabet size (must be a square of an integer)
    :param gray: True to use Gray coding, False otherwise

    >>> import arlpy
    >>> arlpy.comms.iqplot(arlpy.comms.qam(16))
    """
    n = int(_sqrt(m))
    if n*n != m:
        raise ValueError('m must be an integer squared')
    x = _np.empty((n, n), dtype=_np.complex)
    for r in range(n):
        for i in range(n):
            x[r,i] = r + 1j*i
    x -= _np.mean(x)
    x /= _np.std(x)
    x = _np.ravel(x)
    if gray:
        ndx = _np.reshape(gray_code(m), (n,n))
        for i in range(1, n, 2):
            ndx[i] = _np.flipud(ndx[i])
        ndx = invert_map(_np.ravel(ndx))
        x = x[ndx]
    return x

def fsk(m=2, n=None):
    """Generate an m-FSK constellation.

    The concept of signal constellation is generalized to allow vectors to enable
    representation of FSK as signal points. The signal constellation then becomes
    a set of vectors, each vector representing the baseband signal to be used when
    the corresponding symbol is to be transmitted.

    If n is not specified, 2m baseband samples are used per symbol. This ensures
    integral number of transmitted cycles, and avoids discontinuities in the output
    signal. However, the bandwidth efficiency of this choice is poor. A better
    bandwidth efficiency can be obtained by using m baseband samples per symbol, but
    this results in discontinuities that result in frequency leakage. An alternative
    is to use :func:`msk` instead, since it provides good bandwidth efficiency and
    avoids the discontinuities.

    :param m: symbol alphabet size
    :param n: number of baseband samples per symbol

    >>> import arlpy
    >>> x = arlpy.comms.modulate(arlpy.comms.random_data(100, m=2), arlpy.comms.fsk())
    """
    if n is None:
        n = 2*m
    if n < m:
        raise ValueError('n must be >= m')
    f = _np.linspace(-1.0, 1.0, m) * (0.5-0.5/m)
    x = _np.empty((m, n), dtype=_np.complex)
    for i in range(m):
        x[i] = _np.exp(-2j*_pi*f[i]*_np.arange(n))
    return x

def msk():
    """Generate a MSK constellation with 4 baseband samples per 2-bit symbol.

    The concept of signal constellation is generalized to allow vectors to enable
    representation of FSK as signal points. The signal constellation then becomes
    a set of vectors, each vector representing the baseband signal to be used when
    the corresponding symbol is to be transmitted.

    MSK is a special form of a 2-FSK (see :func:`fsk`) constellation that avoids signal
    discontinuities while achieving better bandwidth efficiency. To do this, MSK uses a
    time-varying constellation that depends on the earlier bit transmitted. We can avoid
    the time variation by modeling MSK as a time-invariant constellation with a symbol
    alphabet size of 4.

    >>> import arlpy
    >>> x = arlpy.comms.modulate(arlpy.comms.random_data(50, m=4), arlpy.comms.msk())
    """
    return _np.array([[1,  1j, -1, -1j],
                      [1,  1j, -1,  1j],
                      [1, -1j, -1, -1j],
                      [1, -1j, -1,  1j]], dtype=_np.complex)

def iqplot(data, spec='.', labels=None):
    """Plot signal points.

    :param data: complex baseband signal points
    :param spec: plot specifier (see :func:`matplotlib.pyplot.plot`)
    :param labels: label for each signal point

    >>> import arlpy
    >>> arlpy.comms.iqplot(arlpy.comms.psk(8))
    >>> arlpy.comms.iqplot(arlpy.comms.qam(16), 'rx')
    >>> arlpy.comms.iqplot(arlpy.comms.psk(4), labels=['00', '01', '11', '10'])
    """
    import matplotlib.pyplot as plt
    data = _np.asarray(data)
    if labels is None:
        plt.plot(data.real, data.imag, spec)
    else:
        if labels == True:
            labels = range(len(data))
        for i in range(len(data)):
            plt.text(data[i].real, data[i].imag, str(labels[i]))
    plt.axis([-2, 2, -2, 2])
    plt.grid()
    plt.show()

def modulate(data, const):
    """Modulate data into signal points for the specified constellation.

    The data must use only symbol alphabet defined for the specified constellation.

    :param data: data symbols to modulate
    :param const: constellation to use
    :returns: modulated complex baseband signal

    >>> import arlpy
    >>> x = arlpy.comms.modulate(arlpy.comms.random_data(100), arlpy.comms.psk())
    """
    data = _np.asarray(data, dtype=_np.int)
    const = _np.asarray(const)
    return _np.ravel(const[data])

def demodulate(x, const, metric=None, decision=lambda a: _np.argmin(a, axis=1)):
    """Demodulate complex baseband signal based on the specified constellation.

    :param x: complex baseband signal to demodulate
    :param const: constellation to use
    :param metric: distance metric to use as a measure of closeness of signals
    :param decision: rule for decision making, `None` to return soft decisions
    :returns: demodulated data symbols (or metric in soft decision mode)

    The metric is a function that takes in two signal segments and measures a
    "distance" between them. The smaller the distance (allowed to be negative),
    the closer the signals. Usually one signal is from the constellation while
    the other is a segment of the input signal to demodulate. When unspecified,
    the metric for a complex valued constellation (such as PSK/QAM) is the
    Euclidean distance, for a real valued constellation (such as OOK) is the
    incoherent difference in signal level, and for a vector valued constellation
    is the dot product.

    The decision rule is a function that takes in the metric of all possible
    constellation points and decides on the demodulated data. By default, this
    is the argmin function. If the decision rule is set to `None`, no hard decision
    is made, and the metric is returned as a "soft decision".

    >>> import arlpy
    >>> bpsk = arlpy.comms.psk()
    >>> d1 = arlpy.comms.random_data(100)
    >>> x = arlpy.comms.modulate(d1, bpsk)
    >>> d2 = arlpy.comms.demodulate(x, bpsk)
    >>> arlpy.comms.ber(d1, d2)
    0.0
    """
    if metric is None:
        if const.ndim == 2:
            # multi-dimensional constellation => matched filter
            m, n = const.shape
            metric = lambda a, b: -_np.abs(_np.sum(_np.expand_dims(_np.reshape(a,(len(x)/n, n)), axis=2) * b.conj().T, axis=1))
        elif _np.all(_np.abs(const.imag) < 1e-6) and _np.all(const.real >= 0):
            # all real constellation => incoherent distance
            metric = lambda a, b: _np.abs(_np.abs(a)-b)
        else:
            # general PSK/QAM constellation => Euclidean distance
            metric = lambda a, b: _np.abs(a-b)
    y = metric(_np.expand_dims(x, axis=1), const)
    return y if decision is None else decision(y)

def diff_encode(x):
    """Encode phase differential baseband signal.

    :param x: complex baseband data to encode differentially
    :returns: differentially encoded complex baseband data of length len(x)+1

    >>> import arlpy
    >>> x = arlpy.comms.modulate(arlpy.comms.random_data(100, 4), arlpy.comms.psk(4))   # QPSK
    >>> len(x)
    100
    >>> y = arlpy.comms.diff_encode(x)  # DQPSK
    >>> len(y)
    101
    >>> x[0]
    (0.707+0.707j)
    >>> y[1]/y[0]
    (0.707+0.707j)
    """
    x = _np.asarray(x)
    y = _np.insert(x, 0, 1)
    for j in range(2,len(y)):
        y[j] *= y[j-1]
    return y

def diff_decode(x):
    """Decode phase differential baseband signal.

    :param x: complex baseband differential data to decode
    :returns: decoded complex baseband data of length len(x)-1

    >>> import arlpy
    >>> d1 = arlpy.comms.random_data(100, 4)
    >>> qpsk = arlpy.comms.psk(4)
    >>> x = arlpy.comms.modulate(d1, qpsk)
    >>> y = arlpy.comms.diff_encode(x)
    >>> z = arlpy.comms.diff_decode(y)
    >>> d2 = arlpy.comms.demodulate(z, qpsk)
    >>> arlpy.comms.ser(d1, d2)
    0.0
    """
    x = _np.asarray(x)
    y = _np.array(x)
    y[1:] *= x[:-1].conj()
    return y[1:]

def awgn(x, snr, measured=False):
    """Add Gaussian noise to signal.

    :param x: real passband or complex baseband signal
    :param snr: SNR in dB
    :param measured: True to measure signal strength, False to assume unit strength signal

    >>> import arlpy
    >>> d1 = arlpy.comms.random_data(100, 4)
    >>> qpsk = arlpy.comms.psk(4)
    >>> x = arlpy.comms.modulate(d1, qpsk)
    >>> y = arlpy.comms.awgn(x, 6)
    >>> d2 = arlpy.comms.demodulate(y, qpsk)
    >>> arlpy.comms.ser(d1, d2)
    0.02
    """
    signal = _np.std(x) if measured else 1.0
    noise = signal * _np.power(10, -snr/20.0)
    if x.dtype == _np.complex:
        noise /= _sqrt(2)
        y = x + _np.random.normal(0, noise, _np.shape(x)) + 1j*_np.random.normal(0, noise, _np.shape(x))
    else:
        y = x + _np.random.normal(0, noise, _np.shape(x))
    return y

def ser(x, y):
    """Measure symbol error rate between symbols in x and y.

    :param x: symbol array #1
    :param y: symbol array #2
    :returns: symbol error rate

    >>> import arlpy
    >>> arlpy.comms.ser([0,1,2,3], [0,1,2,2])
    0.25
    """
    x = _np.asarray(x, dtype=_np.int)
    y = _np.asarray(y, dtype=_np.int)
    n = _np.product(_np.shape(x))
    e = _np.count_nonzero(x^y)
    return float(e)/n

def ber(x, y, m=2):
    """Measure bit error rate between symbols in x and y.

    :param x: symbol array #1
    :param y: symbol array #2
    :param m: symbol alphabet size (maximum 64)
    :returns: bit error rate

    >>> import arlpy
    >>> arlpy.comms.ber([0,1,2,3], [0,1,2,2], m=4)
    0.125
    """
    x = _np.asarray(x, dtype=_np.int)
    y = _np.asarray(y, dtype=_np.int)
    if _np.any(x >= m) or _np.any(y >= m) or _np.any(x < 0) or _np.any(y < 0):
        raise ValueError('Invalid data for specified m')
    if m == 2:
        return ser(x, y)
    if m > _MAX_M:
        raise ValueError('m > %d not supported' % (_MAX_M))
    n = _np.product(_np.shape(x))*_np.log2(m)
    e = x^y
    e = e[_np.nonzero(e)]
    e = _np.sum(_popcount[e])
    return float(e)/n

def rcosfir(beta, sps, span=None):
    """Generates a raised cosine FIR filter.

    :param beta: shape of the raised cosine filter (0-1)
    :param sps: number of samples per symbol
    :param span: length of the filter in symbols (`None` => automatic selection)

    >>> import arlpy
    >>> rc = arlpy.comms.rcosfir(0.25, 6)
    >>> bb = arlpy.comms.modulate(arlpy.comms.random_data(100), arlpy.comms.psk())
    >>> pb = arlpy.comms.upconvert(bb, 6, 27000, 18000, rc)
    """
    if beta < 0 or beta > 1:
        raise ValueError('Beta must be between 0 and 1')
    if span is None:
        # from http://www.commsys.isy.liu.se/TSKS04/lectures/3/MichaelZoltowski_SquareRootRaisedCosine.pdf
        # since this recommendation is for root raised cosine filter, it is conservative for a raised cosine filter
        span = 33-int(44*beta) if beta < 0.68 else 4
    delay = int(span*sps/2)
    t = _np.arange(-delay, delay+1, dtype=_np.float)/sps
    denom = 1 - (2*beta*t)**2
    eps = _np.finfo(float).eps
    idx1 = _np.nonzero(_np.abs(denom) > _sqrt(eps))
    b = _np.full_like(t, beta*_sin(_pi/(2*beta))/(2*sps))
    b[idx1] = _np.sinc(t[idx1]) * _cos(_pi*beta*t[idx1])/denom[idx1] / sps
    b /= _sqrt(_np.sum(b**2))
    return b

def rrcosfir(beta, sps, span=None):
    """Generates a root raised cosine FIR filter.

    :param beta: shape of the root raised cosine filter (0-1)
    :param sps: number of samples per symbol
    :param span: length of the filter in symbols (`None` => automatic selection)

    >>> import arlpy
    >>> rrc = arlpy.comms.rrcosfir(0.25, 6)
    >>> bb = arlpy.comms.modulate(arlpy.comms.random_data(100), arlpy.comms.psk())
    >>> pb = arlpy.comms.upconvert(bb, 6, 27000, 18000, rrc)
    """
    if beta < 0 or beta > 1:
        raise ValueError('Beta must be between 0 and 1')
    if span is None:
        # from http://www.commsys.isy.liu.se/TSKS04/lectures/3/MichaelZoltowski_SquareRootRaisedCosine.pdf
        span = 33-int(44*beta) if beta < 0.68 else 4
    delay = int(span*sps/2)
    t = _np.arange(-delay, delay+1, dtype=_np.float)/sps
    b = _np.empty_like(t)
    b[delay] = -1/(_pi*sps) * (_pi*(beta-1)-4*beta)
    eps = _np.finfo(float).eps
    idx2 = _np.nonzero(_np.abs(_np.abs(4*beta*t)-1) < _sqrt(eps))
    if len(idx2) > 0:
        b[idx2] = (_pi*(beta+1)*_sin(_pi*(beta+1)/(4*beta))
                   - 4*beta*_sin(_pi*(beta-1)/(4*beta))
                   + _pi*(beta-1)*_cos(_pi*(beta-1)/(4*beta))) / (2*_pi*sps)
    ind = _np.arange(len(t))
    ind = _np.delete(ind, _np.append(idx2, delay))
    nind = t[ind]
    b[ind] = -4*beta/sps * (_cos((1+beta)*_pi*nind) + _sin((1-beta)*_pi*nind)/(4*beta*nind)) / (_pi*((4*beta*nind)**2-1))
    b /= _sqrt(_np.sum(b**2))
    return b

def upconvert(x, sps, fc, fs=2.0, g=None):
    """Upconvert a complex baseband signal with pulse shaping.

    This function supports upconversion by an integer factor. For a more general
    passband conversion (but without pulse shaping), see :func:`arlpy.signal.bb2pb`.

    If the carrier frequency is 0, the upsampled (at passband sampling rate) and
    pulse shaped complex baseband data is returned. If the pulse shape is `None`,
    a rectangular pulse shape is assumed.

    The upconversion process introduces a group delay depending on the pulse shaping
    filter. It is usually (len(g)-1)/2 passband samples.

    :param x: complex baseband data
    :param sps: number of passband samples per baseband symbol
    :param fc: carrier frequency in Hz
    :param fs: passband sampling rate
    :param g: pulse shaping filter

    >>> import arlpy
    >>> rrc = arlpy.comms.rrcosfir(0.25, 6)
    >>> bb = arlpy.comms.modulate(arlpy.comms.random_data(100), arlpy.comms.psk())
    >>> pb = arlpy.comms.upconvert(bb, 6, 27000, 108000, rrc)
    """
    if g is None:
        g = _np.ones(sps)/_sqrt(sps)  # implied rectangular pulse shaping
    x = _np.asarray(x, dtype=_np.complex)
    y = _sp.upfirdn(g, x, up=sps)
    if fc != 0:
        y *= _sqrt(2)*_np.exp(-2j*_pi*fc*_time(y, fs))
        y = y.real
    return y

def downconvert(x, sps, fc, fs=2.0, g=None):
    """Downconvert a passband signal with a matched pulse shaping filter.

    This function supports downconversion by an integer factor. For a more general
    baseband conversion (but without matched filtering), see :func:`arlpy.signal.pb2bb`.

    If the carrier frequency is 0, the input is assumed to be complex baseband, and only
    undergoes matched filtering and downsampling. If the pulse shape is `None`, a
    rectangular pulse shape is assumed.

    The downconversion process introduces a group delay depending on the matched
    filter. It is usually (len(g)-1)/2 passband samples.

    :param x: real passband data (or complex baseband data at passband sampling rate, if fc=0)
    :param sps: number of passband samples per baseband symbol
    :param fc: carrier frequency in Hz
    :param fs: passband sampling rate
    :param g: pulse shaping filter (for matched filtering)

    >>> import arlpy
    >>> d1 = arlpy.comms.random_data(100, 4)
    >>> qpsk = arlpy.comms.psk(4)
    >>> bb1 = arlpy.comms.modulate(d1, qpsk)
    >>> rrc = arlpy.comms.rrcosfir(0.25, 6)
    >>> pb = arlpy.comms.upconvert(bb1, 6, 27000, 108000, rrc)
    >>> bb2 = arlpy.comms.downconvert(pb, 6, 27000, 108000, rrc)
    >>> delay = (len(rrc)-1)/2   # compute passband group delay of rrc FIR filter
    >>> delay = 2*delay/6        # compute baseband group delay after filtering twice
    >>> d2 = arlpy.comms.demodulate(bb2[delay:-delay], qpsk)
    >>> arlpy.comms.ser(d1, d2)
    0.0
    """
    if g is None:
        g = _np.ones(sps)/_sqrt(sps)  # implied rectangular pulse shaping
    y = _np.array(x, dtype=_np.complex)
    if fc != 0:
        y *= _sqrt(2)*_np.exp(2j*_pi*fc*_time(y, fs))
    y = _sp.upfirdn(g, y, down=sps)
    return y
