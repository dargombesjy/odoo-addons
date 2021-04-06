var NumToWordsIdn = {
  th_val: ['', 'Ribu', 'Juta', 'Milliar', 'Triliun'],
  // th_val = ['','thousand','million', 'milliard','billion'],
  dg_val: ['', 'Satu', 'Dua', 'Tiga', 'Empat', 'Lima', 'Enam', 'Tujuh', 'Delapan', 'Sembilan'],
  tn_val: ['Sepuluh', 'Sebelas', 'Dua Belas', 'Tiga Belas', 'Empat Belas', 'Lima Belas', 'Enam Belas', 'Tujuh Belas', 'Delapan Belas', 'Sembilan Belas'],
  hn_val: ['', 'Seratus', 'Dua Ratus', 'Tiga Ratus', 'Empat Ratus', 'Lima Ratus', 'Enam Ratus', 'Tujuh Ratus', 'Delapan Ratus', 'Sembilan Ratus'],
  tw_val: ['Dua Puluh', 'Tiga Puluh', 'Empat Puluh', 'Lima Puluh', 'Enam Puluh', 'Tujuh Puluh', 'Delapan Puluh', 'Sembilan Puluh'],

  toWordsconver: function (s) {
    s = s.toString();
    s = s.replace(/[\, ]/g, '');
    if (s != parseFloat(s)) {
      return 'not a number';
    }
    var x_val = s.indexOf('.');
    if (x_val == -1) {
      x_val = s.length;
    }
    if (x_val > 15) {
      return 'too big';
    }
    var n_val = s.split('');
    var str_val = '';
    var sk_val = 0;
    for (var i = 0; i < x_val; i++) {
      if ((x_val - i) % 3 == 2) {
        if (n_val[i] == '1') {
          str_val += tn_val[Number(n_val[i + 1])] + ' ';
          i++;
          sk_val = 1;
        } else if (n_val[i] != 0) {
          str_val += tw_val[n_val[i] - 2] + ' ';
          sk_val = 1;
        }
      } else if (n_val[i] != 0) {
        //str_val += dg_val[n_val[i]] + ' ';
        if ((x_val - i) % 3 == 0) {
          str_val += hn_val[n_val[i]] + ' ';
        } else {
          str_val += dg_val[n_val[i]] + ' ';
        }
        //str_val += 'ratus ';
        sk_val = 1;
      }
      if ((x_val - i) % 3 == 1) {
        if (sk_val)
          str_val += th_val[(x_val - i - 1) / 3] + ' ';
        sk_val = 0;
      }
    }

    if (x_val != s.length) {
      var y_val = s.length;
      str_val += 'koma ';
      for (var i = x_val + 1; i < y_val; i++) {
        str_val += dg_val[n_val[i]] + ' ';
      }
    }
    str_val += 'Rupiah';
    return str_val.replace(/\s+/g, ' ');
  }
}